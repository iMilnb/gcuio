{% extends "home.html" %}
{% import "jsmacros.html" as js %}
{% block gerard %}

var mkurl = function(source) {
    var l = source.line;
    $.each(source.urls, function() {
        var r = '<kbd><a href="' + this + '">' + this + '</a></kbd>';
        l = l.replace(this, r);
    });
    return '<span class="line">' + l + '</span>';
}

var process_ircline = function(data, lastdate) {
    $.each(data, function() {
        source = this._source;
        /* do not refresh last line */
        if (source['fulldate'] == lastdate)
            return true
        /* timestamp */
        var ircline = '<div class="small ircline {{ ircline_style["div"] }}" ';
        ircline += 'id="' + source['fulldate'] + '">';

        {{ js.button('time', ircline_style) }}
        {{ js.button('nick', ircline_style) }}
        /* destination nicks */
        {{ js.buttonlst('tonick', ircline_style) }}
        /* real line */
        ircline += mkurl(source);
        /* tags */
        {{ js.buttonlst('tags', ircline_style) }}

        ircline += '</div>';

        $('.irclive').append(ircline);
    });
}

var _getjson = function() {
    var irclive = $('.irclive') /* full IRC div */
    var lastdate = $('.ircline').last().attr('id'); /* last IRC line */
    if (!lastdate) /* first call */
        lastdate = '';
    var irc_last = '{{ url_for("get_irc_last") }}?fromdate=' + lastdate;

    $.getJSON(irc_last, function(data) {
        process_ircline(data, lastdate);
    });

    irclive[0].scrollTop = irclive[0].scrollHeight; /* auto scroll to bottom */
}

$(function() {
    _getjson();

    var auto_refresh = setInterval(function() {
        _getjson();

    }, 5000);

});
{% endblock %}
