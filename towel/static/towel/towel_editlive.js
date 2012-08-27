;(function($) {
    var editLive = function(action, attribute, value) {
        var data = {};
        data[attribute] = value;

        $.post(action, data, function(data) {
            if (typeof(data) == 'string') {
                alert(data);
            } else {
                $.each(data, function(key, value) {
                    if (key == '!redirect') {
                        window.location.href = value;
                        return false;
                    }
                    initForms($('#' + key).html(value).flash());
                });
            }
        });
    }

    // XXX handle the return key too in inputs?
    $(document.body).on('focusout',
            'input[type=text].editlive, textarea.editlive', function(event) {
        var $this = $(this),
            original = $this.data('original'),
            attribute = $this.data('attribute');

        if (this.value == original)
            return;

        editLive($this.data('action'), $this.data('attribute'), this.value);
    });

    $(document.body).on('click',
            'input[type=checkbox].editlive', function(event) {
        var $this = $(this),
            attribute = $this.data('attribute');

        editLive($this.data('action'), $this.data('attribute'),
            $this.attr('checked') ? true : false);
    });

    $(document.body).on('click', 'a.editlive', function(event) {
        event.stopPropagation();
        event.preventDefault();

        var $this = $(this),
            value = $this.data('value'),
            original = $this.data('original');

        if (value == original)
            return;

        editLive($this.data('action'), $this.data('attribute'), value);
    });

    $('form.editlive').each(function() {
        var $form = $(this),
            action = $form.attr('action');

        $form.on('submit', false);
        $form.on('change', 'input[type=text], textarea, select',
            function(event) {
                // TODO what about form prefixes?
                // TODO handle original value
                editLive(action, this.name, this.value);
            });

        // TODO checkboxes etc.
    });
})(jQuery);
