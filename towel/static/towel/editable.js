var TowelEditable = {
    get_editor: function($editor) {
        var init_editor = function(data) {
            if (data.indexOf('{') === 0) {
                $.each($.parseJSON(data), function(key, value) {
                    $('#' + key).html(value);
                });
                return false;
            } else {
                $editor.html(data);
                $editor.find('form').on('submit', function() {
                    $.post(this.action, $(this).serialize(), init_editor);
                    return false;
                });
            }
        };
        return init_editor;
    },

    onclick: function(elem) {
        var $elem = $(elem);
        if ($elem.find('form').length)
            return;

        var qstring = '_editfields=' + $elem.data('editfields').replace(',', '&_editfields=');
        $.get(TowelEditable.editfields_url + qstring, TowelEditable.get_editor($elem));
    },

    init: function(editfields_url) {
        TowelEditable.editfields_url = editfields_url;
        $('body').delegate('.towel_editable', 'click', function() {
            return TowelEditable.onclick(this);
        });
    }
};
