{% extends "home.html" %}
{% block gerard %}
var process_ircline = function(data, lastdate) {
    $.each(data, function(k) {
        source = data[k]['_source'];
        /* do not refresh last line */
        if (source['fulldate'] == lastdate)
            return true
        /* timestamp */
        ircline = '<div class="ircline" id="' + source['fulldate'] + '">';
        /* source nick */
        if (source['nick'] != '') {
            ircline += '<button type="button" class="btn btn-sm btn-success">';
            ircline += source['nick'];
            ircline += '</button>';
        }
        /* destination nicks */
        source['tonick'].forEach(function(nick) {
            ircline += '<button type="button" class="btn btn-sm btn-info">';
            ircline += nick;
            ircline += '</button>';
        });
        /* real line */
        ircline += source['line'];
        /* tags */
        source['tags'].forEach(function(tag) {
            ircline += '<button type="button" class="btn btn-sm btn-warning">';
            ircline += tag;
            ircline += '</button>';
        });
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
