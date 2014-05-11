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

/* generates a popover preview for images */
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
    var l = minimd(escape_html(source.line + ' '));
    /* foreach URLs in line, make them a href */
    $.each(source.urls, function() {
        var eurl = escape_html(this);
        var res = '<kbd><a href="' + eurl + '" target="_blank"';
        /* if it is an image, make it a popover */
        if (_isimg(this))
            res += rabbitify(this)
        res += '>' + eurl + '</a></kbd>';
        /* only replace a complete url (like rhonrhon think it is)
         * so match the last space also
         */
        l = l.replace(eurl + ' ', res + ' ');
    });
    return l;
}

var mktweeturl = function(data) {
    var text = encodeURIComponent('<' + data.nick + '> ' + data.line);
    var via = 'GCUsquad';

    var tweeturl = 'https://twitter.com/share?text=' + text;
    tweeturl += '&via=' + via;

    if ( data.tags ) {
      tweeturl += '&hashtags=' + encodeURIComponent(data.tags.join(','));
    }

    return tweeturl;
}

/* process irc channel window */
var process_ircline = function(data, lastdate, cnt, pos) {
    $.each(data, function() {
        source = this._source;
        /* do not refresh last line */
        if (lastdate && source['fulldate'] == lastdate)
            return true
        /* timestamp */
        var ircline = '<div ';
        ircline += 'class="small {{ ircline_style["div"] }}" ';
        ircline += 'id="' + source['fulldate'] + '">';

        if (lastdate === undefined) { /* on a searchbox */
            {{ js.button('date', ircline_style) }}
        } else {
            {{ js.button('time', ircline_style) }}
        }
        {{ js.button('nick', ircline_style) }}
        /* destination nicks */
        {{ js.buttonlst('tonick', ircline_style) }}
        /* real line */
        ircline += '<span class="line">' + decoline(source) + '</span>';
        /* tags */
        {{ js.buttonlst('tags', ircline_style, 'tag') }}

        ircline += '</div>';

        if (pos == 'append')
            $(cnt).append(ircline);
        else
            $(cnt).prepend(ircline);
    });
}

/* process "links of the day" column */
var process_urlline = function(data, lastdate, cnt, pos) {
    $.each(data, function() {
        source = this._source;
        if (lastdate && source['fulldate'] == lastdate)
            return true;
        var urlline = '';
        var hasimg = false;
        var hastags = false;
        $.each(source.urls, function() {
            var eurl = escape_html(this);
            urlline += '<div class="small list-group-item urlline" ';
            urlline += 'id="' + source.fulldate + '">';
            urlline += '<a href="' + eurl + '" target="_blank" ';
            /* URL is an image, popover is a preview */
            if (_isimg(this)) {
                urlline += rabbitify(this);
                hasimg = true;
            } else {
            /* URL is not an image, popover is an abstract */
                urlline += 'data-content="[' + source.time + '] ';
                urlline += '<span class=\'label label-success bigger-label\'>';
                /* Double escaping needed to avoid XSS in popovers */
                urlline += escape_html(escape_html(source.nick));
                urlline += '</span> ';
                urlline += escape_html(escape_html(source.line)) + ' ';
                if (source.tags.length > 0) {
                    hastags = true;
                    urlline += '<h5>';
                    $.each(source.tags, function() {
                        urlline += '<span class=\'label label-warning\'>';
                        urlline +=  escape_html(escape_html(this)) + ' ';
                        urlline += '<span class=\'glyphicon glyphicon-tag\'>';
                        urlline += '</span></span> ';
                    });
                    urlline += '</h5>';
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

            eurl = eurl.replace(/^https?:\/\/(www\.)?/,'');

            var maxlen = 30;
            if (eurl.length > maxlen)
                eurl = eurl.substr(0, maxlen - 1) + "&hellip;";
            urlline += eurl + '</a></div>';
        });
        if (pos == 'append')
            $(cnt).append(urlline);
        else
            $(cnt).prepend(urlline);
    });
    
}

var _getjson = function(t, todate) {
    var live = $('.' + t + 'live'); /* full div */
    var lastdate;
    var action;
    var get_last = '{{ url_for("get_last") }}?';
    get_last += 't=' + encodeURIComponent(t); /* type: irc or url */

    if (todate) { /* todate was given, we're fetching previous results */
        lastdate = $('.' + t + 'line').first().attr('id');
        get_last += '&k=to';
        action = 'prepend';
    } else { /* normal call, fetch last entries */
        lastdate = $('.' + t + 'line').last().attr('id');
        action = 'append';
    }

    if (!lastdate) {/* first call */
        lastdate = '';
        this['sh_' + t] = 0; /* record type scroll height */
    }

    get_last += '&d=' + encodeURIComponent(lastdate);

    var doscroll = false;
    /* fetch scrollbar position */
    var livepos = live.prop('scrollTop') + live.prop('offsetHeight');
    /* at bottom, auto scroll to next results */
    if (livepos >= live.prop('scrollHeight'))
        doscroll = true;

    var fn =  window['process_' + t + 'line']; /* build generic function */
    $.getJSON(get_last, function(data) {
        if (typeof fn === "function")
            fn(data, lastdate, '.' + t + 'live', action);
    });

    /* autoscroll only if we're at the bottom (i.e. now scrolling) */
    if (!lastdate || doscroll) {
        /* autoscroll to bottom */
        live.prop({ scrollTop: live.prop('scrollHeight') });
        live.css('border-bottom', std_border_bottom);
    } else if (this['sh_' + t] < live.prop('scrollHeight'))
        live.css('border-bottom', hl_border_bottom);

    /* proportional positionning if we're going back in history */
    if (todate) {
        var ratio = live.children().length / {{ nlines }};
        live.prop({ scrollTop: live.prop('scrollHeight') / ratio })
    }

    /* record last scrollHeight */
    this['sh_' + t] = live.prop('scrollHeight');
}

var _searchjson = function(q, f) {
    /* wipe old content */
    $('.searchbox').empty();

    var search = '{{ url_for("search") }}?q=';
    search += encodeURIComponent(q) + '&f=' + encodeURIComponent(f);

    var total = 0;
    $.getJSON(search, function(data) {
        if (!data.hits)
            data = { 'hits': [], 'total': 0 }

        process_ircline(data.hits, undefined, '.searchbox');
        total = data.total;
    });
    $('#total').html(' (' + total + ' r&eacute;sultats)');

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

var modal_display = function(q, t) {
    var f = 0;
    if (q) {
        /* a query was given, 1st search */
        modal_display._q = q;
        modal_display._f = 0;
    } else {
        /* no query, take the recorded one */
        q = modal_display._q;
        f = modal_display._f;
    }

    if (t == 'next') {
        f += {{ nlines }}
        modal_display._f = f;
    }
    if (t == 'prev') {
        f -= {{ nlines }}
        modal_display._f = f;
    }

    _searchjson(q, f);

    $('#searchModal').modal({});

}

var _refresh = function(w) {
    _getjson(w, undefined);

    /* must be refreshed for every new entry */
    $('[data-toggle="popover"]').popover({
                                            trigger: 'hover',
                                            html: true,
                                            container: 'body'
                                        });
    $('[data-toggle="tooltip"]').tooltip({
                                            trigger: 'hover',
                                            html: true,
                                            container: 'body'
                                        });
}

var _refresh_stats = function() {
    var stats_url = '{{ url_for("status") }}';

    var stats = 0;
    $.getJSON(stats_url, function(data) {
        stats = data.active_connections;
    });
    $('#stats').html(stats);
}

var _refresh_chaninfos = function() {
    var chaninfos_url = '{{ url_for("chaninfos") }}';

    var topic = '';
    var users = [];
    var ops = [];
    $.getJSON(chaninfos_url, function(data) {
        topic = data.topic;
        users = data.users;
        ops = data.ops;
    });
    var maxlen = 80;
    var eol = '@@EOL@@';
    var umark = '@@URL@@';
    if (topic.length > maxlen) {
        topic = [topic.slice(0, maxlen), eol, topic.slice(maxlen)].join('');
        maxlen = false;
    }

    var re = new RegExp('(https?:\/\/[^\\\s]+)', 'g')
    urls = topic.match(re);
    topic = topic.replace(re, umark);
    topic = escape_html(topic);
    $.each(urls, function() {
        eurl = escape_html(this);
        url = '<a href=\'' + eurl + '\'>' + eurl + '</a>';
        topic = topic.replace(umark, url);
    });
    
    /* update topic tooltip */
    $('#topic').attr('data-original-title', topic.replace(eol, ''));
    /* topic was > maxlen, cut it and finish it with ... */
    if (!maxlen) {
        re = new RegExp(eol + '.*')
        topic = topic.replace(re, '&hellip;')
    }
    /* display channel topic */
    $('#topic').html(topic);
    /* display actual IRC users */
    $('#chaninfos').html(users.length);

    /* refresh ircers (users) popover list */
    var ircers = users.sort().join(', ');
    $('#ircers').attr('data-content', ircers);
}

var _check_height = function(t) {
    var live = $('.' + t + 'live'); /* full div */

    live.scroll(function() {
        /* user is at the bottom of div  */
        var livepos = live.prop('scrollTop') + live.prop('offsetHeight');
        if (livepos >= live.prop('scrollHeight')) {
            live.css('border-bottom', std_border_bottom);
        }
        /* user is on top of div, load previous lines */
        if (live.prop('scrollTop') == 0)
            _getjson(t, true);
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

    /* load these two before main refresh so popovers are correctly updated */
    _refresh_stats();
    _refresh_chaninfos();
    $.each(['irc', 'url'], function() {
        _refresh(this);
        _check_height(this);
    });

    /* main search */
    var search = $('input[class="form-control"]');
    search.keypress(function(event) {
        if (event.which == 13) {
            /* no date specified */
            modal_display(search.val(), undefined);
            /* needed so the modal does not disappear */
            return false;
        };
    });

    /* modal next search results */
    $('#next-results').on('click', function() {
        modal_display(undefined, 'next');
        return false;
    });

    /* modal prev search results */
    $('#prev-results').on('click', function() {
        modal_display(undefined, 'prev');
        return false;
    });

    /* set the timer to refresh data every 5 seconds */
    var auto_refresh = setInterval(function() {
        _refresh_stats();
        _refresh_chaninfos();
        _refresh('irc');
        _refresh('url');
    }, 8000);

});
{% endblock %}
