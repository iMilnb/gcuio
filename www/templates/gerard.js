{% extends "home.html" %}
{% import "jsmacros.html" as js %}
{% block gerard %}

var htmlesc = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '\\\\': '&#92;',
};

var escape_html = function(data) {
    $.each(htmlesc, function(k, v) {
        var re = new RegExp(k, 'g');
        data = data.replace(re, v);
    });
    /* https://www.owasp.org/index.php/XSS_%28Cross_Site_Scripting%29_Prevention_Cheat_Sheet */
    return data;
}

var std_border_bottom = '1px solid black';
var hl_border_bottom = '1px solid #5090ff';

var _isimg = function(url) {
    if (url.match(/\.(jpe?g|gif|png|bmp)$/i))
        return true
    return false
}

var mkmark = function(mark, repl, line) {
    var rx = '(^|\\\s)' + mark + '([^' + mark + ']+)' + mark + '(\\\s|$)';

    re = new RegExp(rx, 'g');

    return line.replace(re, '$1<' + repl + '>' + '$2' + '</' + repl + '>$3')
}

var minimd = function(str) {
    var mds = {
        '`': 'code',
        '_': 'em',
        '\\\*': 'strong',
    };

    $.each(mds, function(k, v) {
        str = mkmark(k, v, str);
    });

    return str;
}

var rabbitify = function(url) {
    var img = escape_html(escape_html(url));
    img = '<img src=\'' + img + '\' width=\'200\'>';
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
            return true;
        var urlline = '';
        var hasimg = false;
        var hastags = false;
        $.each(source.urls, function() {
            /* TODO not too restrictive replace() */
            var eurl = encodeURI(this);
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
                /* Double escaping needed to avoid XSS in popovers */
                urlline += escape_html(escape_html(source.nick));
                urlline += '</span><br />';
                urlline += escape_html(escape_html(source.line)) + ' ';
                urlline += '<br />';
                if (source.tags.length > 0) {
                    hastags = true;
                    $.each(source.tags, function() {
                        urlline += '<span class=\'label label-warning\'>';
                        urlline +=  escape_html(escape_html(this)) + ' ';
                        urlline += '<span class=\'glyphicon glyphicon-tag\'>';
                        urlline += '</span></span> ';
                    });
                }
                urlline += '" ';
                urlline += 'data-placement="auto" ';
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
    if (!lastdate) {/* first call */
        lastdate = '';
        this['sh_' + t] = 0;
    }
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
    if (!lastdate || doscroll) {
        /* autoscroll to bottom */
        live.prop({ scrollTop: live.prop('scrollHeight') });
        live.css('border-bottom', std_border_bottom);
    } else if (this['sh_' + t] < live.prop('scrollHeight'))
        live.css('border-bottom', hl_border_bottom);

    /* record last scrollHeight */
    this['sh_' + t] = live.prop('scrollHeight');
}

var _searchjson = function(q, f) {
    /* wipe old content */
    $('.searchbox').empty();

    var search = '{{ url_for("search") }}?q=' + q + '&f=' + f;

    var total = 0;
    $.getJSON(search, function(data) {
        process_ircline(data.hits, undefined, '.searchbox');
        total = data.total;
    });

    if (total < 1)
        $('.searchbox').append('Pas de r&eacute;sultats');

    if (f + {{ nlines }} >= total)
        $('#next-results').hide();
    else
        $('#next-results').show();

    if (f < {{ nlines }})
        /* we're on the first result page, don't show "previous" */
        $('#prev-results').hide();
    else
        $('#prev-results').show();

    $('.searchbox [data-toggle="popover"]').popover({
                                                container: '.modal-body',
                                                html: true,
                                                trigger: 'hover'
                                            });

    return f;
}

var modal_display = function(q) {

    var f = _searchjson(q, 0);

    $('#searchModal').modal({});

    /* next search results */
    $('#next-results').on('click', function() {
        f = _searchjson(q, f + {{ nlines }});
        return false;
    });

    /* prev search results */
    $('#prev-results').on('click', function() {
        f = _searchjson(q, f - {{ nlines }});
        return false;
    });

}

var _refresh = function(w) {
    _getjson(w);

    /* must be refreshed for every new entry */
    $('[data-toggle="popover"]').popover({
                                            trigger: 'hover',
                                            html: true,
                                            container: 'body'
                                        });
}

var _check_height = function(t) {
    var live = $('.' + t + 'live'); /* full div */

    live.scroll(function() {
        var livepos = live.prop('scrollTop') + live.prop('offsetHeight');
        if (livepos >= live.prop('scrollHeight')) {
            live.css('border-bottom', std_border_bottom);
        }
    });
}

var _async_ajax = function(b) {
    $.ajaxSetup({
        async: b
    });
}

$(function() {
    /* synchronous ajax queries mess up first display plus scrolling pos. */
    _async_ajax(false)

    $.each(['irc', 'url'], function() {
        _refresh(this);
        _check_height(this);
    });

    /* main search */
    var search = $('input[class="form-control"]');
    search.keypress(function(event) {
        if (event.which == 13) {
            /* no date specified */
            modal_display(search.val(), 0);
            /* needed so the modal does not disappear */
            return false;
        };
    });

    /* set the timer to refresh data every 5 seconds */
    var auto_refresh = setInterval(function() {
        _refresh('irc');
        _refresh('url');
    }, 5000);

});
{% endblock %}
