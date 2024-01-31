function changeActiveLink(link) {
    // Retirer la classe 'active' de tous les liens
    var links = document.getElementsByTagName('a');
    for (var i = 0; i < links.length; i++) {
      links[i].classList.remove('active');
    }

    // Ajouter la classe 'active' au lien cliqué
    link.classList.add('active');
  }

function toogleSideBar() {
  // document.querySelector(".footer").classList.add('sidebarActive');
  // document.querySelector("#content").classList.add('sidebarActive');
  // $('.sidebarCollapse').on('click', function () {
  //   $('#sidebar').toggleClass('active');
  //   document.querySelector("#content").classList.toggle('sidebarActive');
  //   document.querySelector(".topbar").classList.toggle('sidebarActive');
  //   document.querySelector(".footer").classList.toggle('sidebarActive');
  // })
  document.querySelector("#sidebar").classList.toggle('active');
}