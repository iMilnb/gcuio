{% extends "home.html" %}
{% import "jsmacros.html" as js %}
{% block gerard %}

var escape_html = function(data) {
    return data.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

var mkurl = function(source) {
    var l = escape_html(source.line);
    $.each(source.urls, function() {
        var r = '<kbd><a href="' + this + '">' + this + '</a></kbd>';
        l = l.replace(this, r);
    });
    return l;
}

var process_ircline = function(data, lastdate) {
    $.each(data, function() {
        source = this._source;
        /* do not refresh last line */
        if (source['fulldate'] == lastdate)
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
        ircline += '<span class="line">' + mkurl(source) + '</span>';
        /* tags */
        {{ js.buttonlst('tags', ircline_style) }}

        ircline += '</div>';

        $('.irclive').append(ircline);
    });
}

var process_urlline = function(data, lastdate) {
    $.each(data, function() {
        source = this._source;
        if (source['fulldate'] == lastdate)
            return true
        var urlline = '';
        var urldate = source.fulldate;
        $.each(source.urls, function() {
            urlline += '<div class="small list-group-item urlline" ';
            urlline += 'id="' + urldate + '">'
            urlline += '<a href="' + this + '">' + this + '</a>';
            urlline += '</div>';
        });
        $('.urllive').append(urlline);
    });
    
}

var _getjson = function(t) {
    var live = $('.' + t + 'live'); /* full div */
    var lastdate = $('.' + t + 'line').last().attr('id');
    if (!lastdate) /* first call */
        lastdate = '';
    var get_last = '{{ url_for("get_last") }}?t=' + t + '&d=' + lastdate;

    var fn =  window['process_' + t + 'line'];
    $.getJSON(get_last, function(data) {
        if (typeof fn === "function")
            fn(data, lastdate);
    });

    live.prop({ scrollTop: live.prop("scrollHeight") });
}

$(function() {
    _getjson('irc');
    _getjson('url');

    var auto_refresh = setInterval(function() {
        _getjson('irc');
        _getjson('url');

    }, 5000);

});
{% endblock %}
