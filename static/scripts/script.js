toggle = (x)  => {
  if ($("input[name=" + x + "]").prop("checked")) {
    $("input[name=" + x + "]").prop("checked", false);
  } else {
    $("input.menu").prop("checked", false);
    $("input[name=" + x + "]").prop("checked", true);
  }
}

open_media = (index) => {
    var main = document.getElementById(index);
    main.style.display = "flex"; 
}

close_media = () => {
  document.body.style.overflow = 'scroll';
  document.querySelector('input[name="popup"]').checked = false;
  document.querySelector('input[name="popup"]').checked = false;
  //location.reload(true);
}

upload = (url, data) => {
  console.log(url);
  
  $.ajax({ url: url
         , type: "POST"
         , enctype: "multipart/form-data"
         , data: data
         , processData: false
         , contentType: false
         , xhr: function() {
                  var xhr = $.ajaxSettings.xhr();
       
                  xhr.upload.onloadstart = function() {
                    $("section#upload").hide();
                    $("section#progress").show();
                    $("section#progress .loading").show();
                  };
       
                  xhr.upload.onprogress = function(e) {
                    $("#progress .loader").css("width", "" + (100 * e.loaded/e.total) + "%");
                  };
       
                  xhr.upload.onload = function() {
                   $("section#progress .loading").hide();
                   $("section#progress .saving").show();
                  };
       
                  return xhr;
                }

         , success: function(response) {
                      console.log(response.status);
                      alert('Upload done');
                      window.location.reload(true);
                    }
         , error: function() {
                    console.log('General error occured', 'e');
                    alert('Upps, something went wrong');
                    window.location.reload(true);
                  }
         , complete: function() {}
         });
  }

$(document).ready(function() {

  $('input[name=category] + select').change(function () {
    $('input[name=category]').val(this.value);
    $(this).val('0');
  });

  $('div.radiobox:not(.sub)').change(function () {
     $('div.radiobox.sub + select').val('0');
  });

  $('div.radiobox.sub').click(function() {
    // $('div.radiobox.sub + select').attr('size', '6');
  });

  $('div.radiobox.sub + select').change(function () {
     $(this).prev().find('input[value="user"]').prop('checked', true);
  });

  $('#profile_import form').submit(function(e) {
    e.preventDefault();
    $('html').animate({ scrollTop: 0 }, 1000);
    var data = new FormData($('section#profile_import form')[0]);
    upload('/profile/import', data)
  });

  $("#upload form").submit(function(e) {
    e.preventDefault();
    $("html").animate({ scrollTop: 0 }, 1000);
    var data = new FormData($("section#upload form")[0]);
    upload('/files/upload', data)
  });
});
