;(function($) {
    var editLive = function(action, attribute, value) {
        var data = {};
        data[attribute] = value;

        $.post(action, data, function(data) {
            if (typeof(data) == 'string') {
                alert(data);
            } else {
                $.each(data, function(key, value) {
                    initForms($('#' + key).html(value).flash());
                });

                $('textarea.autogrow').autogrow();
            }
        });
    }

    // XXX handle the return key too in inputs?
    $(document).on('focusout', 'input[type=text].editlive, textarea.editlive', function() {
        var $this = $(this),
            original = $this.data('original'),
            attribute = $this.data('attribute');

        if (this.value == original)
            return;

        editLive($this.data('action'), $this.data('attribute'), this.value);
    });

    $(document).on('click', 'input[type=checkbox].editlive', function() {
        var $this = $(this),
            attribute = $this.data('attribute');

        editLive($this.data('action'), $this.data('attribute'),
            $this.attr('checked') ? true : false);
    });

    $(document).on('click', 'a.editlive', function() {
        var $this = $(this),
            value = $this.data('value'),
            original = $this.data('original');

        if (value == original)
            return false;

        editLive($this.data('action'), $this.data('attribute'), value);

        return false;
    });
})(jQuery);
