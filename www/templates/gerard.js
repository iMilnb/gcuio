{% extends "home.html" %}
{% import "jsmacros.html" as js %}
{% block gerard %}

var escape_html = function(data) {
    return data.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

var rabbitify = function(url) {
    if (url.match(/\.(jpe?g|gif|png|bmp)$/)) {
        var img = '<img src=\'' + url + '\' width=\'200\'>';
        var data = 'data-toggle="popover" data-content="' + img + '" ';
        data += 'data-placement="auto"';
        return data;
    }
    return '';
}

var mkurl = function(source) {
    var l = escape_html(source.line);
    $.each(source.urls, function() {
        var eurl = encodeURI(this);
        var r = '<kbd><a href="' + eurl + '" target="_blank"';
        r += rabbitify(eurl) + '>'
        r += eurl + '</a></kbd>';
        l = l.replace(this, r);
    });
    return l;
}

var minimd = function(str) {
    var s = str.replace(/`(.+?)`/g, '<code>$1</code>');
    s = s.replace(/_(.+?)_/g, '<em>$1</em>');
    s = s.replace(/\*(.+?)\*/g, '<strong>$1</strong>');

    return s;
}

var process_ircline = function(data, lastdate, cnt) {
    $.each(data, function() {
        source = this._source;
        /* do not refresh last line */
        if (lastdate && source['fulldate'] == lastdate)
            return true
        /* timestamp */
        var ircline = '<div ';
        ircline += 'class="small {{ ircline_style["div"] }}" ';
        ircline += 'id="' + source['fulldate'] + '">';

        {{ js.button('time', ircline_style) }}
        {{ js.button('nick', ircline_style) }}
        if (source.tonick[0])
            ircline += '<span class="glyphicon glyphicon-chevron-right"></span>';
        /* destination nicks */
        {{ js.buttonlst('tonick', ircline_style) }}
        /* real line */
        ircline += '<span class="line">' + minimd(mkurl(source)) + '</span>';
        /* tags */
        {{ js.buttonlst('tags', ircline_style, 'tag') }}

        ircline += '</div>';

        $(cnt).append(ircline);
    });
}

var process_urlline = function(data, lastdate, cnt) {
    $.each(data, function() {
        source = this._source;
        if (lastdate && source['fulldate'] == lastdate)
            return true
        var urlline = '';
        $.each(source.urls, function() {
            urlline += '<div class="small list-group-item urlline" ';
            urlline += 'id="' + source.fulldate + '">';
            urlline += '<a href="' + escape_html(this) + '" target="_blank" ';
            var imgdata = rabbitify(this);
            if (imgdata == '') {
                urlline += 'data-content="[' + source.time + '] ';
                urlline += '<' + escape_html(source.nick) + '> ';
                urlline +=  escape_html(source.line) + ' ';
                if (source.tags.length > 0) {
                    $.each(source.tags, function() {
                        urlline += '&#9873; ' + escape_html(this) + ' ';
                    });
                }
                urlline += '" ';
                urlline += 'data-placement="left" ';
                urlline += 'data-container="body" ';
                urlline += 'data-toggle="popover"';
            } else
                urlline += imgdata;
            urlline += '><span class="glyphicon glyphicon-globe"></span> ';
            urlline += escape_html(this).replace(/https?:\/\//,'') + '</a>';
            urlline += '</div>';
        });
        $(cnt).append(urlline);
    });
    
}

var _getjson = function(t) {
    var live = $('.' + t + 'live'); /* full div */
    var lastdate = $('.' + t + 'line').last().attr('id');
    if (!lastdate) /* first call */
        lastdate = '';
    var get_last = '{{ url_for("get_last") }}?t=' + t + '&d=' + lastdate;

    var doscroll = false;
    var livepos = live.prop('scrollTop') + live.prop('offsetHeight');

    if (livepos >= live.prop('scrollHeight'))
        doscroll = true;

    var fn =  window['process_' + t + 'line']; /* build generic function */
    $.getJSON(get_last, function(data) {
        if (typeof fn === "function")
            fn(data, lastdate, '.' + t + 'live');
    });

    /* autoscroll only if we're at the bottom (i.e. now scrolling) */
    if (!lastdate || doscroll)
        live.prop({ scrollTop: live.prop('scrollHeight') });
}

var modal_display = function(k, v) {
    var search = '{{ url_for("search") }}?k=' + k + '&v=' + v;
    $('.modal-body').empty();
    $.getJSON(search, function(data) {
        process_ircline(data, undefined, '.modal-body');
    });
    $('#searchModal').modal();
}

var _refresh = function() {
    _getjson('irc');
    _getjson('url');

    $('[data-toggle="popover"]').popover({trigger: 'hover', html: true});
}

var _async_ajax = function(b) {
    $.ajaxSetup({
        async: b
    });
}

$(function() {
    /* synchronous ajax queries mess up first display plus scrolling pos. */
    _async_ajax(false)

    _refresh();

    var search = $('input[class="form-control"]');
    search.keypress(function(event) {
        if (event.which == 13) {
            modal_display('line', search.val().replace(/ +/g, ','));
        };
    });

    var auto_refresh = setInterval(function() {
        _refresh();
    }, 5000);

});
{% endblock %}
