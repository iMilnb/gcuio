{% extends "home.html" %}
{% import "jsmacros.html" as js %}
{% block gerard %}
var process_ircline = function(data, lastdate) {
    $.each(data, function() {
        source = this._source;
        /* do not refresh last line */
        if (source['fulldate'] == lastdate)
            return true
        /* timestamp */
        ircline = '<div class="{{ ircline_style["div"] }}" ';
        ircline += 'id="' + source['fulldate'] + '">';

        {{ js.button('time', ircline_style) }}
        {{ js.button('nick', ircline_style) }}
        /* destination nicks */
        {{ js.buttonlst('tonick', ircline_style) }}
        /* real line */
        ircline += source['line'];
        /* tags */
        {{ js.buttonlst('tags', ircline_style) }}

        ircline += '</div>';

        $('#irclive').append(ircline);
    });
}

var _getjson = function() {
    var lastdate = $('.ircline').last().attr('id');
    if (!lastdate) /* first call */
        lastdate = '';
    var irc_last = '{{ url_for("get_irc_last") }}?fromdate=' + lastdate;

    $.getJSON(irc_last, function(data) {
        process_ircline(data, lastdate);
    });
}

$(function() {
    _getjson();

    var auto_refresh = setInterval(function() {
        _getjson();
    }, 5000);

});
{% endblock %}
