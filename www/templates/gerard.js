{% extends "home.html" %}
{% import "jsmacros.html" as js %}
{% block gerard %}

var escape_html = function(data) {
    return data.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

var _isimg = function(url) {
    if (url.match(/\.(jpe?g|gif|png|bmp)$/i))
        return true
    return false
}

var rabbitify = function(url) {
    var img = '<img src=\'' + url + '\' width=\'200\'>';
    var data = 'data-toggle="popover" data-content="' + img + '" ';
    data += 'data-placement="auto"';
    return data;
}
/* replaces line URLs with clickable links and apply minimal markdown*/
var decoline = function(source) {
    /* minimal markdown */
    var l = minimd(escape_html(source.line));
    /* foreach URLs in line, make them a href */
    $.each(source.urls, function() {
        var eurl = encodeURI(this);
        var res = '<kbd><a href="' + eurl + '" target="_blank"';
        /* if it is an image, make it a popover */
        if (_isimg(eurl))
            res += rabbitify(eurl)
        res += '>' + eurl + '</a></kbd>';
        l = l.replace(this, res);
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
        ircline += '<span class="line">' + decoline(source) + '</span>';
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
        var hasimg = false;
        var hastags = false;
        $.each(source.urls, function() {
            var eurl = encodeURI(this.replace(/[^\/a-z0-9]$/i, ''));
            urlline += '<div class="small list-group-item urlline" ';
            urlline += 'id="' + source.fulldate + '">';
            urlline += '<a href="' + eurl + '" target="_blank" ';
            /* URL is an image, popover is a preview */
            if (_isimg(eurl)) {
                urlline += rabbitify(eurl);
                hasimg = true;
            } else {
            /* URL is not an image, popover is an abstract */
                urlline += 'data-content="[' + source.time + '] ';
                urlline += '<span class=\'label label-success\'>';
                urlline += escape_html(source.nick) + '</span><br />';
                urlline += escape_html(source.line) + ' ';
                urlline += '<br />';
                if (source.tags.length > 0) {
                    hastags = true;
                    $.each(source.tags, function() {
                        urlline += '<span class=\'label label-warning\'>';
                        urlline +=  escape_html(this) + ' ';
                        urlline += '<span class=\'glyphicon glyphicon-tag\'>';
                        urlline += '</span></span> ';
                    });
                }
                urlline += '" ';
                urlline += 'data-placement="auto" ';
                urlline += 'data-container="body" ';
                urlline += 'data-toggle="popover"';
            }
            /* what is actually shown in LotD div */
            if (hasimg)
                urlline += '><span class="glyphicon glyphicon-film"></span> ';
            else if (hastags)
                urlline += '><span class="glyphicon glyphicon-tag"></span> ';
            else
                urlline += '><span class="glyphicon glyphicon-globe"></span> ';

            urlline += eurl.replace(/https?:\/\//,'') + '</a>';
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

var modal_display = function(k, v, d) {
    if (k && v) {
        modal_display._key = k;
        modal_display._val = v;
    } else {
        k = modal_display._key;
        v = modal_display._val;
    }
    console.log(k + ' ' + v + ' ' + d);
    if (!d)
        d = '';
    var search = '{{ url_for("search") }}?k=' + k + '&v=' + v + '&d=' + d;
    $('.searchbox').empty();
    $.getJSON(search, function(data) {
        process_ircline(data, d, '.searchbox');
    });
    $('#searchModal').modal({});
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

    /* main search */
    var search = $('input[class="form-control"]');
    var stype = 'line';
    search.keypress(function(event) {
        if (event.which == 13) {
            modal_display(stype, search.val().replace(/ +/g, ','), undefined);
            /* needed so the modal does not disappear */
            return false;
        };
    });

    /* next search results */
    $('#next-results').on('click', function() {
        var lastdate = $('.searchbox .ircline').last().attr('id');
        modal_display(undefined, undefined, lastdate);
        return false;
    });

    /* change search type */
    $(".dropdown-menu").on('click', 'li a', function() {
        stype = $(this).prop('id'); /* get type from menu id */
        $(".dropdown-toggle").html($(this).text() + ' &#9660;'); /* v arrow */
    });

    /* set the timer to refresh data every 5 seconds */
    var auto_refresh = setInterval(function() {
        _refresh();
    }, 5000);

});
{% endblock %}
