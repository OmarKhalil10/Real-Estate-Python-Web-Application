$(document).ready(function() {
    $(window).scroll(function () {
  
      if ($(window).scrollTop() > 70) {
        $('#navbar').addClass('sticky');
        console.log('yaaa')
      }
  
      if ($(window).scrollTop() < 71) {
        $('#navbar').removeClass('sticky');
        console.log('noooo')
      }
    });
  });