// var jQuery;
var wterm = {};

jQuery(function($){
  var formID = '#sshForm',
      submitBtn = $('#submit'),
      info = $('#info'),
      toolbar = $('#toolbar'),
      toggle = $('#toggle'),
      progress = $("#progress"),
      // uploader = $("#upload"),
      terminal = $('#term'),
      style = {},
      defaultTitle = '',
      titleElement = document.querySelector('title'),
      customizedFont = document.fonts ? document.fonts.values().next().value : undefined,
      defaultFonts,
      DISCONNECTED = 0,
      CONNECTING = 1,
      CONNECTED = 2,
      state = DISCONNECTED,
      messages = {1: 'This client is connecting ...', 2: 'This client is already connnected.'},
      maxKeySize = 16384,
      fields = ['hostname', 'port', 'username', 'password'],
      formKeys = fields.concat(['password', 'totp']),
      optsKeys = ['bgcolor', 'title', 'encoding', 'command', 'term'],
      urlFormData = {},
      urlOptsData = {},
      validatedFormData,
      eventOrigin,
      // term = new window.Terminal();
      term = new window.Terminal({
        cursorBlink: true,
        theme: {
          background: urlOptsData.bgcolor || 'black'
        }
      });


  // Hide toolbar first
  toolbar.hide();
  toggle.hide();

  function copySelectedText() {
    let el = document.createElement('textarea');
    el.value = term.getSelection();
    el.select();
    document.execCommand('copy');
  }

  // Store hostname, port, username in local storage
  function storeItems(names, data) {
    names.forEach((name) => {
      value = data[name];
      if (value){
        window.localStorage.setItem(name, value);
      }
    });
  }

  // Restore hostname, port, username from local storage
  function restoreItems(names) {
    names.forEach((name) => {
      value = window.localStorage.getItem(name);
      if (value) {
        $(`#${name}`).val(value);
      }
    })
  }

  function setSession(name, data) {
    window.sessionStorage.clear()
    console.log(window.sessionStorage)
    window.sessionStorage.setItem(name, data)
    console.log(window.sessionStorage)
  }

  function getSession(name) {
    return window.sessionStorage.getItem(name)
  }


  function parseXtermStyle() {
    var text = $('.xterm-helpers style').text();
    var arr = text.split('xterm-normal-char{width:');
    style.width = parseFloat(arr[1]);
    arr = text.split('div{height:');
    style.height = parseFloat(arr[1]);
  }

  function getCellSize(term) {
    style.width = term._core._renderService._renderer.dimensions.actualCellWidth;
    style.height = term._core._renderService._renderer.dimensions.actualCellHeight;
  }

  function currentGeometry(term) {
    if (!style.width || !style.height) {
      try {
        getCellSize(term);
      } catch (TypeError) {
        parseXtermStyle();
      }
    }

    var cols = parseInt(window.innerWidth / style.width, 10) - 1;
    var rows = parseInt(window.innerHeight / style.height, 10);
    return {'cols': cols, 'rows': rows};
  }

  function resizeTerminal(term) {
    var geometry = currentGeometry(term);
    // term.onResize(geometry.cols, geometry.rows);
    term.on_resize(geometry.cols, geometry.rows);

  }

  function setBackgoundColor(term, color) {
    term.setOption('theme', {
      background: color
    });
  }

  function isCustomFontLoaded() {
    if (!customizedFont) {
      console.log('No custom font specified.');
    } else {
      console.log('Status of custom font ' + customizedFont.family + ': ' + customizedFont.status);
      if (customizedFont.status === 'loaded') {
        return true;
      }
      if (customizedFont.status === 'unloaded') {
        return false;
      }
    }
  }

  function updateFontFamily(term) {
    if (term.font_family_updated) {
      console.log('Already using custom font family');
      return;
    }

    if (!defaultFonts) {
      defaultFonts = term.getOption('fontFamily');
    }

    if (isCustomFontLoaded()) {
       var new_fonts =  customizedFont.family + ', ' + defaultFonts;
      var new_fonts =  "Hack" + ', ' + defaultFonts;
      term.setOption('fontFamily', new_fonts);
      term.font_family_updated = true;
      console.log('Using custom font family ' + new_fonts);
    }
  }

  function resetFontFamily(term) {
    if (!term.font_family_updated) {
      console.log('Already using default font family');
      return;
    }

    if (defaultFonts) {
      term.setOption('fontFamily',  defaultFonts);
      term.font_family_updated = false;
      console.log('Using default font family ' + defaultFonts);
    }
  }

  function formatGeometry(cols, rows) {
    return JSON.stringify({'cols': cols, 'rows': rows});
  }

  function readTextWithDecoder(file, callback, decoder) {
    var reader = new window.FileReader();

    if (decoder === undefined) {
      decoder = new window.TextDecoder('utf-8', {'fatal': true});
    }

    reader.onload = function() {
      var text;
      try {
        text = decoder.decode(reader.result);
      } catch (TypeError) {
        console.log('Decoding error happened.');
      } finally {
        if (callback) {
          callback(text);
        }
      }
    };

    reader.onerror = function(e) {
      console.error(e);
    };

    reader.readAsArrayBuffer(file);
  }

  function readTextWithEncoding(file, callback, encoding) {
    var reader = new window.FileReader();

    if (encoding === undefined) {
      encoding = 'utf-8';
    }

    reader.onload = function() {
      if (callback) {
        callback(reader.result);
      }
    };

    reader.onerror = function(e) {
      console.error(e);
    };

    reader.readAsText(file, encoding);
  }

  function readFileAsText(file, callback, decoder) {
    if (!window.TextDecoder) {
      readTextWithEncoding(file, callback, decoder);
    } else {
      readTextWithDecoder(file, callback, decoder);
    }
  }

  function resetWssh() {
    var name;

    for (name in wterm) {
      if (wterm.hasOwnProperty(name) && name !== 'connect') {
        delete wterm[name];
      }
    }
  }

  function setMsg(text) {
    // status.html(text.split('\n').join('<br/>'));
    // $('#status').html(text.split('\n').join('<br/>'));
    // $('#status').html(`<br/>${text}`);
    $('#msg').html(text);
  }

  function ajaxCallback(resp) {
    console.log("ajaxCallback");
    submitBtn.attr('disabled', false);
    console.log(resp.status, resp.statusText);

    if (resp.status !== 200) {
      setMsg(resp.status + ': ' + resp.statusText);
      return;
    }

    let msg = resp.responseJSON;
    console.log(msg);
    if (!msg.id) {
      setMsg(msg.status);
      return;
    } else {
      setSession("minion", msg.id)
    }

    // Prepare websocket
    console.log(window.location);
    let proto = window.location.protocol,
        url = window.location.href,
        char = (proto === 'http:' ? 'ws:': 'wss:'),
        wsURL = `${url.replace(proto, char)}ws?id=${msg.id}`,
        sock = new window.WebSocket(wsURL),
        encoding = 'utf-8',
        decoder = window.TextDecoder ? new window.TextDecoder(encoding) : encoding,
        terminal = document.getElementById('terminal')
        // term = new window.Terminal({
        //   cursorBlink: true,
        //   theme: {
        //     background: urlOptsData.bgcolor || 'black'
        //   }
        // });
    term.fitAddon = new window.FitAddon.FitAddon();
    term.loadAddon(term.fitAddon);

    console.log(msg);
    if (!msg.encoding) {
      console.log('Unable to detect the default encoding of your server');
      msg.encoding = encoding;
    } else {
      console.log('The deault encoding of your server is ' + msg.encoding);
    }

    function termWrite(text) {
      if (term) {
        term.write(text);
        if (!term.resized) {
          resizeTerminal(term);
          term.resized = true;
        }
      }
    }

    function setEncoding(new_encoding) {
      // for console use
      if (!new_encoding) {
        console.log('An encoding is required');
        return;
      }

      if (!window.TextDecoder) {
        decoder = new_encoding;
        encoding = decoder;
        console.log('Set encoding to ' + encoding);
      } else {
        try {
          decoder = new window.TextDecoder(new_encoding);
          encoding = decoder.encoding;
          console.log('Set encoding to ' + encoding);
        } catch (RangeError) {
          console.log('Unknown encoding ' + new_encoding);
          return false;
        }
      }
    }

    wterm.setEncoding = setEncoding;

    if (urlOptsData.encoding) {
      if (setEncoding(urlOptsData.encoding) === false) {
        setEncoding(msg.encoding);
      }
    } else {
      setEncoding(msg.encoding);
    }


    wterm.geometry = function() {
      // for console use
      var geometry = currentGeometry(term);
      console.log('Current window geometry: ' + JSON.stringify(geometry));
    };

    wterm.send = function(data) {
      // for console use
      if (!sock) {
        console.log('Websocket was already closed');
        return;
      }

      if (typeof data !== 'string') {
        console.log('Only string is allowed');
        return;
      }

      try {
        JSON.parse(data);
        sock.send(data);
      } catch (SyntaxError) {
        data = data.trim() + '\r';
        sock.send(JSON.stringify({'data': data}));
      }
    };

    wterm.reset_encoding = function() {
      // for console use
      if (encoding === msg.encoding) {
        console.log('Already reset to ' + msg.encoding);
      } else {
        setEncoding(msg.encoding);
      }
    };

    wterm.resize = function(cols, rows) {
      // for console use
      if (term === undefined) {
        console.log('Terminal was already destroryed');
        return;
      }

      var valid_args = false;

      if (cols > 0 && rows > 0)  {
        var geometry = currentGeometry(term);
        if (cols <= geometry.cols && rows <= geometry.rows) {
          valid_args = true;
        }
      }

      if (!valid_args) {
        console.log('Unable to resize terminal to geometry: ' + formatGeometry(cols, rows));
      } else {
        term.on_resize(cols, rows);
      }
    };

    wterm.set_bgcolor = function(color) {
      setBackgoundColor(term, color);
    };

    wterm.custom_font = function() {
      updateFontFamily(term);
    };

    wterm.default_font = function() {
      resetFontFamily(term);
    };

    term.on_resize = function(cols, rows) {
      if (cols !== this.cols || rows !== this.rows) {
        console.log('Resizing terminal to geometry: ' + formatGeometry(cols, rows));
        this.resize(cols, rows);
        sock.send(JSON.stringify({'resize': [cols, rows]}));
      }
    };

    term.onData(function(data) {
      // console.log(data);
      sock.send(JSON.stringify({'data': data}));
    });

    // Copy on selection
    window.addEventListener('mouseup', copySelectedText);

    sock.onopen = function() {
      toggle.toggle()
      // toolbar.show();
      // progress.hide();

      term.open(terminal);
      // toggleFullscreen(term);

      //Full screen
      $('#terminal .terminal').toggleClass('fullscreen');
      term.fitAddon.fit();

      updateFontFamily(term);
      term.focus();
      state = CONNECTED;
      titleElement.text = urlOptsData.title || defaultTitle;
      if (urlOptsData.command) {
        setTimeout(function() {
          sock.send(JSON.stringify({'data': urlOptsData.command+'\r'}));
        }, 500);
      }
    };

    sock.onmessage = function(msg) {
      readFileAsText(msg.data, termWrite, decoder);
    };

    sock.onerror = function(e) {
      console.error(e);
    };

    sock.onclose = function(e) {
      // Hide toolbar again
      toolbar.hide();
      toggle.hide();

      term.dispose();
      term = undefined;
      sock = undefined;
      resetWssh();
      setMsg(e.reason);
      state = DISCONNECTED;
      defaultTitle = 'Term1nal';
      titleElement.text = defaultTitle;

      // Remove some event listeners
      window.removeEventListener("mouseup", copySelectedText);
    };

    $(window).resize(function(){
      if(term) {
        resizeTerminal(term);
      }
    });
  } // ajaxCallback()

  function wrapObject(opts) {
    var obj = {};

    obj.get = function(attr) {
      return opts[attr] || '';
    };

    obj.set = function(attr, val) {
      opts[attr] = val;
    };

    return obj;
  }


  function validateFormData() {
    let form = document.querySelector(formID)
    let data = new FormData(form)
    let result = {error: ""}

    fields.forEach(function(attr){
      var val = data.get(attr)
      if (!val) {
        result.error = `${attr} is required`;
        return result;
      } else {
        result[attr] = val;
      }
    })
    
    storeItems(fields.slice(0, -1), result);
    return result;
  }

  function connect() {
    // Use data in the form
    let form = document.querySelector(formID),
        url = form.action,
        data;

    console.log(`[connect()]: ${url}`);
    data = new FormData(form);

    submitBtn.attr('disabled', true)

    $.ajax({
        url: url,
        type: 'post',
        data: data,
        complete: ajaxCallback,
        cache: false,
        contentType: false,
        processData: false
    });
  }

  function crossOriginConnect(event)
  {
    console.log(event.origin);
    var prop = 'connect',
        args;

    try {
      args = JSON.parse(event.data);
    } catch (SyntaxError) {
      args = event.data.split('|');
    }

    if (!Array.isArray(args)) {
      args = [args];
    }

    try {
      eventOrigin = event.origin;
      wterm[prop].apply(wterm, args);
    } finally {
      eventOrigin = undefined;
    }
  }

  wterm.connect = connect;

  $(formID).submit(function(event){
    // Clean msg
    setMsg("");
    event.preventDefault();
    let result = validateFormData();
    if (result.error) {
      setMsg(result.error);
    } else {
      connect();
    }
  });

  $("#upload").click(function(){
    // Clean this for triggering change event for same file
    this.value = "";
    // Clean info text
    info.text("");
  });

  // Listen to "file" change event to upload file,
  // monitor "progress" event to calculate uploading percentage
  $("#upload").change(function(){
    var file = this.files[0]
    var formData = new FormData()
    formData.append("minion", getSession("minion"))
    formData.append("upload", file)

    $.ajax({
      url: '/upload',
      type: "POST",
      data: formData,
      cache: false,
      contentType: false,
      processData: false,
      timeout: 60000,
      async: true,

      xhr: function() {
        var theXHR = $.ajaxSettings.xhr();
        if(theXHR.upload) {
          progress.show();
          theXHR.upload.addEventListener('progress', function(e){
            if(e.lengthComputable){
              percent = Math.ceil(e.loaded / e.total * 100);
              // console.log(percent);
              $(progress).attr("value", percent);
              if(percent == 100) {
                progress.hide();
              }
            }
          }, false);
        }
        return theXHR;
      },
      success: function(data) {
        info.text(data);
      },
      error: function(error) {
        progress.hide()
        console.log(error)
      }
    }); //.ajax()
  }); // #upload.change()

  $("#download").click(function(){
    file = $("#downloadFile").val()
    if (file === "") {
      alert("Input file path")
      return
    }

    // Chrome save dialog will open after file has been downloaded
    // fetch(`download?filepath=${file}&minion=${getSession("minion")}`)
    // .then((resp) =>{
    //   if (!resp.ok) {
    //     alert(`${file} not exist`)
    //   } else {
    //     resp.blob().then((blob) => {
    //       let url = window.URL.createObjectURL(blob);
    //       let a = document.createElement('a');
    //       a.style.display = 'none';
    //       a.href = url;
    //       a.download = file.split('/').pop();
    //       document.body.appendChild(a);
    //       a.click();
    //       window.URL.revokeObjectURL(url)
    //     })
    //   }
    // })
    // .catch((err) => {
    //   alert(err)
    // })

    // With Chrome download progress
    // window.location.href = `download?filepath=${file}&minion=${getSession("minion")}`;
    window.open(`download?filepath=${file}&minion=${getSession("minion")}`);
  }); // #download.click()

  toggle.click(function(){
    $("#downloadFile").val("");
    progress.hide();
    toolbar.toggle();
    info.text("")
  })


  window.addEventListener('message', crossOriginConnect, false);
  $(window).on('beforeunload', function(evt) {
    console.log(evt);
    // Use 'beforeunload' to prevent "ctrl+W" from closing browser tab
    return "bye";
  });

  if (document.fonts) {
    document.fonts.ready.then(
      function() {
        if (isCustomFontLoaded() === false) {
          document.body.style.fontFamily = customizedFont.family;
        }
      }
    );
  }
  // Restore Hostname, Port and Username(exclude Password) in sshForm
  restoreItems(fields.slice(0, -1));
});
