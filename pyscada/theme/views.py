import json
import time
from pyscada.hmi.models import GroupDisplayPermission
from pyscada.utils import get_group_display_permission_list
from pyscada.hmi.models import View
from pyscada.core import version as core_version
import traceback
import pyscada.hmi.models
from pyscada.models import RecordedData, VariableProperty, Variable, Device
from pyscada.models import Log
from pyscada.models import DeviceWriteTask, DeviceReadTask
from pyscada.hmi.models import ControlItem
from pyscada.hmi.models import Form
from pyscada.hmi.models import GroupDisplayPermission
from pyscada.hmi.models import Widget
from pyscada.hmi.models import CustomHTMLPanel
from pyscada.hmi.models import Chart
from pyscada.hmi.models import View
from pyscada.hmi.models import ProcessFlowDiagram
from pyscada.hmi.models import Pie
from pyscada.hmi.models import Page
from pyscada.hmi.models import SlidingPanelMenu
from pyscada.utils import gen_hiddenConfigHtml, get_group_display_permission_list

from django.template.response import TemplateResponse
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.views.decorators.csrf import requires_csrf_token
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models.fields.related import OneToOneRel

import time
import json
import logging

logger = logging.getLogger(__name__)

UNAUTHENTICATED_REDIRECT = (
    settings.UNAUTHENTICATED_REDIRECT
    if hasattr(settings, "UNAUTHENTICATED_REDIRECT")
    else "/accounts/login/"
)


def unauthenticated_redirect(func):
    def wrapper(*args, **kwargs):
        if not args[0].user.is_authenticated:
            return redirect("%s?next=%s" % (UNAUTHENTICATED_REDIRECT, args[0].path))
        return func(*args, **kwargs)

    return wrapper

@unauthenticated_redirect
def view_overview(request):
    page_list = Page.objects.all()
    
    if GroupDisplayPermission.objects.count() == 0:
        view_list = View.objects.all()
    else:
        view_list = get_group_display_permission_list(
            View.objects, request.user.groups.all()
        )

    c = {
        "user": request.user,
        "view_list": view_list,
        "page_list": page_list,
        "version_string": core_version,
        "link_target": settings.LINK_TARGET
        if hasattr(settings, "LINK_TARGET")
        else "_blank",
    }
    return TemplateResponse(
        request, "view_overviewthemesidebar.html", c
    )  # HttpResponse(t.render(c))


@unauthenticated_redirect
@requires_csrf_token
def view(request, link_title):
    base_template = "base.html"
    view_template = "view_themesidebar.html"
    page_template = get_template("content_page.html")
    widget_row_template = get_template("widget_row.html")
    STATIC_URL = (
        str(settings.STATIC_URL) if hasattr(settings, "STATIC_URL") else "static"
    )

    try:
        v = (
            get_group_display_permission_list(View.objects, request.user.groups.all())
            .filter(link_title=link_title)
            .first()
        )
        if v is None:
            raise View.DoesNotExist
        # v = View.objects.get(link_title=link_title)
    except View.DoesNotExist as e:
        logger.warning(f"{request.user} has no permission for view {link_title}")
        raise PermissionDenied("You don't have access to this view.")
    except View.MultipleObjectsReturned as e:
        logger.error(f"{e} for view link_title", exc_info=True)
        raise PermissionDenied(f"Multiples views with this link : {link_title}")
        # return HttpResponse(status=404)

    if v.theme is not None:
        base_template = str(v.theme.base_filename) + ".html"
        view_template = str(v.theme.view_filename) + ".html"

    visible_objects_lists = {}
    items = [
        field
        for field in GroupDisplayPermission._meta.get_fields()
        if issubclass(type(field), OneToOneRel)
    ]
    if GroupDisplayPermission.objects.count() == 0:
        # no groups
        for item in items:
            item_str = item.related_model.m2m_related_model._meta.object_name.lower()
            visible_objects_lists[
                f"visible_{item_str}_list"
            ] = item.related_model.m2m_related_model.objects.all().values_list(
                "pk", flat=True
            )
        visible_objects_lists["visible_page_list"] = v.pages.all().values_list(
            "pk", flat=True
        )
        visible_objects_lists[
            "visible_slidingpanelmenu_list"
        ] = v.sliding_panel_menus.all().values_list("pk", flat=True)
    else:
        for item in items:
            item_str = item.related_model.m2m_related_model._meta.object_name.lower()
            visible_objects_lists[
                f"visible_{item_str}_list"
            ] = get_group_display_permission_list(
                item.related_model.m2m_related_model.objects, request.user.groups.all()
            ).values_list(
                "pk", flat=True
            )
        visible_objects_lists["visible_page_list"] = get_group_display_permission_list(
            v.pages, request.user.groups.all()
        ).values_list("pk", flat=True)
        visible_objects_lists[
            "visible_slidingpanelmenu_list"
        ] = get_group_display_permission_list(
            v.sliding_panel_menus, request.user.groups.all()
        ).values_list(
            "pk", flat=True
        )

    panel_list = SlidingPanelMenu.objects.filter(
        id__in=visible_objects_lists["visible_slidingpanelmenu_list"]
    ).filter(
        position__in=(
            1,
            2,
        )
    )
    control_list = SlidingPanelMenu.objects.filter(
        id__in=visible_objects_lists["visible_slidingpanelmenu_list"]
    ).filter(position=0)

    pages_html = ""
    object_config_list = dict()
    custom_fields_list = dict()
    exclude_fields_list = dict()
    javascript_files_list = list()
    css_files_list = list()
    show_daterangepicker = False
    has_flot_chart = False
    add_context = {}

    for page_pk in visible_objects_lists["visible_page_list"]:
        # process content row by row
        page = Page.objects.get(id=page_pk)
        current_row = 0
        widget_rows_html = ""
        main_content = list()
        sidebar_content = list()
        topbar = False

        show_daterangepicker_temp = False
        show_timeline_temp = False

        for widget in page.widget_set.all():
            # check if row has changed
            if current_row != widget.row:
                # render new widget row and reset all loop variables
                widget_rows_html += widget_row_template.render(
                    {
                        "row": current_row,
                        "main_content": main_content,
                        "sidebar_content": sidebar_content,
                        "sidebar_visible": len(sidebar_content) > 0,
                        "topbar": topbar,
                    },
                    request,
                )
                current_row = widget.row
                main_content = list()
                sidebar_content = list()
                topbar = False
            if widget.pk not in visible_objects_lists["visible_widget_list"]:
                continue
            if not widget.visible:
                continue
            if widget.content is None:
                continue
            widget_extra_css_class = (
                widget.extra_css_class.css_class
                if widget.extra_css_class is not None
                else ""
            )
            mc, sbc, opts = widget.content.create_panel_html(
                widget_pk=widget.pk,
                widget_extra_css_class=widget_extra_css_class,
                user=request.user,
                visible_objects_lists=visible_objects_lists,
            )
            if mc is None:
                logger.info(
                    f"User {request.user} not allowed to see the content of widget {widget}"
                )
            elif mc == "":
                logger.info(f"Content of widget {widget} is empty")
            else:
                main_content.append(dict(html=mc, widget=widget, topbar=sbc))
            if sbc is not None:
                sidebar_content.append(dict(html=sbc, widget=widget))
            if type(opts) == dict and "topbar" in opts and opts["topbar"] == True:
                topbar = True
            if (
                type(opts) == dict
                and "show_daterangepicker" in opts
                and opts["show_daterangepicker"] == True
            ):
                show_daterangepicker = True
                show_daterangepicker_temp = True
            if (
                type(opts) == dict
                and "show_timeline" in opts
                and opts["show_timeline"] == True
            ):
                show_timeline_temp = True
            if type(opts) == dict and "flot" in opts and opts["flot"]:
                has_flot_chart = True
            if type(opts) == dict and "base_template" in opts:
                base_template = opts["base_template"]
            if type(opts) == dict and "view_template" in opts:
                view_template = opts["view_template"]
            if type(opts) == dict and "add_context" in opts:
                add_context.update(opts["add_context"])
            if type(opts) == dict and "javascript_files_list" in opts:
                for file_src in opts["javascript_files_list"]:
                    if {"src": file_src} not in javascript_files_list:
                        javascript_files_list.append({"src": file_src})
            if type(opts) == dict and "css_files_list" in opts:
                for file_src in opts["css_files_list"]:
                    if {"src": file_src} not in css_files_list:
                        css_files_list.append({"src": file_src})
            if (
                type(opts) == dict
                and "object_config_list" in opts
                and type(opts["object_config_list"] == list)
            ):
                for obj in opts["object_config_list"]:
                    model_name = str(obj._meta.model_name).lower()
                    if model_name not in object_config_list:
                        object_config_list[model_name] = list()
                    if obj not in object_config_list[model_name]:
                        object_config_list[model_name].append(obj)
            if (
                type(opts) == dict
                and "custom_fields_list" in opts
                and type(opts["custom_fields_list"] == list)
            ):
                for model in opts["custom_fields_list"]:
                    custom_fields_list[str(model).lower()] = opts["custom_fields_list"][
                        model
                    ]

            if (
                type(opts) == dict
                and "exclude_fields_list" in opts
                and type(opts["exclude_fields_list"] == list)
            ):
                for model in opts["exclude_fields_list"]:
                    exclude_fields_list[str(model).lower()] = opts[
                        "exclude_fields_list"
                    ][model]

        widget_rows_html += widget_row_template.render(
            {
                "row": current_row,
                "main_content": main_content,
                "sidebar_content": sidebar_content,
                "sidebar_visible": len(sidebar_content) > 0,
                "topbar": topbar,
            },
            request,
        )

        pages_html += page_template.render(
            {
                "page": page,
                "widget_rows_html": widget_rows_html,
                "show_daterangepicker": show_daterangepicker_temp,
                "show_timeline": show_timeline_temp,
            },
            request,
        )

    # Generate javascript files list
    if has_flot_chart:
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/jquery/jquery.tablesorter.min.js"}
        )
        # tablesorter parser for checkbox
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/jquery/parser-input-select.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/lib/jquery.mousewheel.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.canvaswrapper.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.colorhelpers.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.saturated.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.browser.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.drawSeries.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.errorbars.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.uiConstants.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.logaxis.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.symbol.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.flatdata.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.navigate.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.fillbetween.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.stack.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.touchNavigate.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.hover.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.touch.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.time.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.axislabels.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.selection.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.composeImages.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.legend.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.pie.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.crosshair.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/flot/source/jquery.flot.gauge.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/jquery.flot.axisvalues.js"}
        )

    if show_daterangepicker:
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/daterangepicker/moment.min.js"}
        )
        javascript_files_list.append(
            {"src": STATIC_URL + "pyscada/js/daterangepicker/daterangepicker.min.js"}
        )

    javascript_files_list.append(
        {"src": STATIC_URL + "pyscada/js/pyscada/pyscada_v0-7-0rc14.js"}
    )

    javascript_files_list.append(
        {"src": STATIC_URL + "pyscada/js/theme/inviseo-theme.js"}
    )

    # Generate css files list
    css_files_list.append(
        {"src": STATIC_URL + "pyscada/css/daterangepicker/daterangepicker.css"}
    )

    # Adding SlidingPanelMenu to hidden config
    for s_pk in visible_objects_lists["visible_slidingpanelmenu_list"]:
        s = SlidingPanelMenu.objects.get(id=s_pk)
        if s.control_panel is not None:
            for obj in s.control_panel._get_objects_for_html(obj=s):
                if obj._meta.model_name not in object_config_list:
                    object_config_list[obj._meta.model_name] = list()
                if obj not in object_config_list[obj._meta.model_name]:
                    object_config_list[obj._meta.model_name].append(obj)
    # Generate html object hidden config
    pages_html += '<div class="hidden globalConfig2">'
    for model, val in sorted(object_config_list.items(), key=lambda ele: ele[0]):
        pages_html += '<div class="hidden ' + str(model) + 'Config2">'
        for obj in val:
            pages_html += gen_hiddenConfigHtml(
                obj,
                custom_fields_list.get(model, None),
                exclude_fields_list.get(model, None),
            )
        pages_html += "</div>"
    pages_html += "</div>"

    context = {
        "base_html": base_template,
        "include": [],
        "page_list": Page.objects.filter(
            id__in=visible_objects_lists["visible_page_list"]
        ),
        "pages_html": pages_html,
        "panel_list": panel_list,
        "control_list": control_list,
        "user": request.user,
        "visible_control_element_list": visible_objects_lists[
            "visible_controlitem_list"
        ],
        "visible_form_list": visible_objects_lists["visible_form_list"],
        "view_title": v.title,
        "view_link_title": link_title,
        "view_show_timeline": v.show_timeline,
        "version_string": core_version,
        "link_target": settings.LINK_TARGET
        if hasattr(settings, "LINK_TARGET")
        else "_blank",
        "javascript_files_list": javascript_files_list,
        "css_files_list": css_files_list,
    }
    context.update(add_context)

    return TemplateResponse(request, view_template, context)