let open_dialog = (x) => {
  let input = document.querySelector(`input[name=${x}]`);
  input.checked = true;
}

let close_dialog = (x) => {
  let input = document.querySelector(`input[name=${x}]`);
  input.checked = false;
}

let toggle = (x)  => {
  window.flash.style.display = 'none';
  let input = document.querySelector(`input[name=${x}]`);
  if (input.checked) input.checked = false;
  else {
    let all = document.getElementsByClassName("toggle");
    Array.from(all).forEach((item) => item.checked = false);
    input.checked = true;
  }
};

let media_toogle = (e, index) => {
  e.preventDefault();
  var media = document.getElementById(`media${index}`);
  if (media.style.display == 'flex') media.style.display = 'none';
  else {
    var imgs = document.querySelectorAll(`#media${index} img`);
    Array.from(imgs).forEach((img) => {
      img.src = img.dataset.src;
    });
    media.style.display = 'flex'
  };
}

let upload = (url, data, ready, fail) => {
  let progress = document.querySelector('section#progress');
  let bar = document.querySelector('section#progress > div');
  let text = document.querySelector('section#progress > div > p');

  let request = new XMLHttpRequest();
  request.open('post', url, true);
  request.setRequestHeader('X-Type', 'Ajax');
  
  request.upload.onloadstart = (e) => {
    progress.style.display = 'block';
    bar.style.width = '0%';
    text.innerText = '0%';
  };

  request.upload.onprogress = (e) => {
  	let percent = (e.loaded / e.total) * 100;
    bar.style.width = `${percent}%`;
    text.innerText = `${Math.round(percent)}%`;
  };

  request.upload.onload = (e) => {
    text.innerText = 'Please wait ...';
  };

  request.onreadystatechange = (e) => {
    if (request.readyState == 4) {
      if (request.status == 200) {
        response = JSON.parse(request.responseText);

        progress.style.display = 'none';
        bar.style.width = '0%';

        alert_update(response, []);
        if (ready) ready(response);

      } else {
        console.log('error');
        if (fail) fail();

      }
    }
  };

  request.send(data);
};

let handle_select_helper = (e) => {
  e.preventDefault();
  let input = document.querySelectorAll('input[name=category]');
  Array.from(input).forEach((item) => item.value = e.target.value);
  e.target.value = '0';
};

let handle_uploads_form = (e) => {
  e.preventDefault();
  let data = new FormData(e.target);
  let url = e.target.getAttribute('action');
  upload(url, data, (resp) => {
    window.location.reload(true);
  });
};

let handle_capture_form = (e) => {
  e.preventDefault();
  let url = e.target.getAttribute('action');
  let canvas = document.querySelector('canvas.capture');
  e.target['canvas'].value = canvas.toDataURL();
  // e.target.submit();
  upload(url, new FormData(e.target));
};

let handle_delete_check = (e) => {
  let button = e.target.querySelector('input[type=submit]');

  if (!button.classList.contains('active')) {
    e.preventDefault();
    button.classList.add('active');

    // Wait 3 sec to remove active status again
    window.setTimeout((e) => {
      button.classList.remove('active');
    }, 3000);
  }
}

let alert_update = (info, error) => {
  alert_clear();

  let message = (text, type) => {
    let p = document.createElement('p');
    p.innerText = text;
    p.classList.add(type);
    window.flash_inner.appendChild(p);
  };

  if (error && error.length > 0) {
    error.forEach((item) => message(item, 'error'));
    window.flash.style.display = 'block';

  } else if (info && info.length > 0) {
    info.forEach((item) => message(item, 'info'));
    window.flash.style.display = 'block';
  }
};

let alert_clear = (e) => {
  window.flash.style.display = 'none';
  window.flash_inner.innerHTML = '';
};

let capture = (e) => {
  e.preventDefault();
  let canvas = document.querySelector('canvas');
  let video = document.getElementById('video');
  let scale = 300 / video.videoWidth;

  canvas.width = video.videoWidth * scale;
  canvas.height = video.videoHeight * scale;
  canvas.setAttribute('width', canvas.width);
  canvas.setAttribute('height', canvas.height);

  ctx = canvas.getContext("2d");
  ctx.scale(1, 1);
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  open_dialog('capture');
}

let tags_set_input = (target) => {
  let childs = [...target.querySelectorAll('.tag')];
  let list = childs.map((element) => element.innerText);
  let input = target.querySelector('input[name=tags]');
  input.value = list;
};

let tags_set_focus = (e) => {
  e.preventDefault();

  let next = e.target.querySelector('input[name=tag]');
  next.focus();
};

let tags_prevent_submit = (e) => {
  if (e.keyCode == 9 || e.keyCode == 13) {
    e.preventDefault();
  }
};

let tags_handle_input = (e) => {
  e.preventDefault();

  if ((e.keyCode == 8 || e.keyCode == 46) && e.target.value.length < 1) {
    /* remove last tag element */
    let list = e.target.parentElement.parentElement;
    let childs = [...list.querySelectorAll('.tag')];

    if (childs.length > 0) {
      childs.pop().remove();
    }

    /* update hidden input field */
    tags_set_input(list);
    return;
  }

  if (e.keyCode == 9 || e.keyCode == 13) {
    if (e.target.value.length > 0) {
      /* add a new tag element */
      let list = e.target.parentElement.parentElement;
      let tag = document.createElement('div');

      tag.classList.add('tag');
      tag.innerHTML = e.target.value;
      list.insertBefore(tag, list.lastElementChild);
      e.target.value = '';
      e.target.style.width = '15px';

      /* update hidden input field */
      tags_set_input(list);
    }

  } else {
    e.target.style.width = ((e.target.value.length + 1) * 15) + 'px';
  }
};

window.onload = (e) => {};
