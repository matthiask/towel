;var TowelEditable = {
    get_editor: function($editor) {
        var init_editor = function(data) {
            if (data.indexOf('{') === 0) {
                $.each($.parseJSON(data), function(key, value) {
                    $('#' + key).html(value);
                });
                $editor.trigger({
                    type: 'updateSuccessful',
                    data: data
                });
                return false;
            } else {
                $editor.html(data);
                $editor.find('form').on('submit', function() {
                    $.post(this.action, $(this).serialize(), init_editor);
                    return false;
                });
                $editor.trigger({
                    type: 'formLoaded',
                    target: this
                });
            }
        };
        return init_editor;
    },

    onclick: function(elem) {
        var $elem = $(elem);
        if ($elem.find('form').length)
            return;

        var editfields = $elem.data('edit'),
            qstring = '_edit=' + $elem.data('edit').replace(/[,\s]+/g, '&_edit=');

        if (editfields)
            $.get(TowelEditable.edit_url + qstring, TowelEditable.get_editor($elem));
    },

    init: function(edit_url) {
        TowelEditable.edit_url = edit_url + (edit_url.indexOf('?')===-1 ? '?' : '&');
        $('body').delegate('.towel_editable', 'click', function() {
            return TowelEditable.onclick(this);
        });
    }
};
