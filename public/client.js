// client-side js
// run by the browser each time your view template is loaded

// by default, you've got jQuery,
// add other scripts at the bottom of index.html

$(function() {
  console.log('hello world :o');
  
  $.get('/dreams', function(dreams) {
    dreams.forEach(function(dream) {
      $('<li></li>').text(dream).appendTo('ul#dreams');
    });
  });

  $('form').submit(function(event) {
    event.preventDefault();
    dream = $('input').val();
    $.post('/dreams?' + $.param({'dream': dream}), function() {
      $('<li></li>').text(dream).appendTo('ul#dreams');
      $('input').val('');
      $('input').focus();
    });
  });

});


// Sliders

var slider = document.getElementById('song-progress');

noUiSlider.create(slider, {
	start: [ 20 ],
	range: {
		'min': [   0 ],
		'max': [ 100 ]
	}
});

var slider = document.getElementById('song-volume');

noUiSlider.create(slider, {
	start: [ 90 ],
	range: {
		'min': [   0 ],
		'max': [ 100 ]
	}
});


// Tooltips

$(function () {
  $('[data-toggle="tooltip"]').tooltip()
})

// Viewport Heights

$(window).on("resize load", function(){

  var totalHeight = $(window).height();

  var headerHeight = $('.header').outerHeight();
  var footerHeight = $('.current-track').outerHeight();
  var playlistHeight = $('.playlist').outerHeight();
  var nowPlaying = $('.playing').outerHeight();

  var navHeight = totalHeight - (headerHeight + footerHeight + playlistHeight + nowPlaying);
  var artistHeight = totalHeight - (headerHeight + footerHeight);

  console.log(totalHeight);

  $(".navigation").css("height" , navHeight);
  $(".artist").css("height" , artistHeight);
  $(".social").css("height" , artistHeight);

});





// Collapse Toggles

$(".navigation__list__header").on( "click" , function() {

  $(this).toggleClass( "active" );

});


// Media Queries

$(window).on("resize load", function(){
	if ($(window).width() <= 768){

    $(".collapse").removeClass("in");

    $(".navigation").css("height" , "auto");

    $(".artist").css("height" , "auto");

	}
});

$(window).on("resize load", function(){
	if ($(window).width() > 768){

    $(".collapse").addClass("in");

	}
});




