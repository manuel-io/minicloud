class Diashow {

  constructor(dias, next) {
    this.count = 0;
    this.length = dias.length;
    this.dias = dias;
    this.bar = document.getElementById('bar');
    this.bartext = document.getElementById('status');

    dias.forEach((dia, index) => {
      this.dias[index].img.src = this.dias[index].path;
      this.dias[index].img.onload = () => this.count++;
    });

    Diashow._load_img(() => {
      /* wait until all images are loaded */
      /* console.log((this.count * 100 / this.length) + ' %'); */
      this.bar.style.width = (this.count * 100 / this.length) + '%';
      this.bartext.innerHTML = this.count + ' of ' + this.length + '<br>images'
      return this.count == this.length;
    }, () => {
      return next();
    });
  }

  static _load_img(check, next) {
    if (check()) next();
    else setTimeout(() => {
      Diashow._load_img(check, next);
    }, 1000);
  }
}
