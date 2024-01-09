function changeActiveLink(link) {
    // Retirer la classe 'active' de tous les liens
    var links = document.getElementsByTagName('a');
    for (var i = 0; i < links.length; i++) {
      links[i].classList.remove('active');
    }

    // Ajouter la classe 'active' au lien cliqué
    link.classList.add('active');
  }