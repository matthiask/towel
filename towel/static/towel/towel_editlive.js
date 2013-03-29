;(function($) {
    var updateLive = function(data) {
        $.each(data, function(key, value) {
            if (key == '!redirect') {
                window.location.href = value;
                return false;
            } else if (key[0] == '!') {
                // unknown command, skip.
                return;
            }

            var elem = $('#' + key),
                update = elem.data('update') || 'replace';

            switch(update) {
                case 'append':
                    elem.append(value);
                    break;
                case 'prepend':
                    elem.prepend(value);
                    break;
                default:
                    elem.html(value);
            }

            elem.trigger('updateLive', [elem]);
        });
    };
    if (!window.updateLive) window.updateLive = updateLive;

    var editLive = function(action, attribute, value) {
        var data = {};
        data[attribute] = value;

        $.post(action, data, function(data) {
            if (typeof(data) == 'string') {
                alert(data);
            } else {
                return updateLive(data);
            }
        });
    }

    var formFieldHandler = function(event) {
        var $this = $(this),
            action = $(this).data('action'),
            original = $this.data('original'),
            attribute = $this.data('attribute');

        if (!action || this.value == original)
            return;

        editLive(action, $this.data('attribute'), this.value);
    }

    // XXX handle the return key too in inputs?
    $(document.body).on('focusout',
        'input[type=text].editlive, textarea.editlive',
        formFieldHandler);
    $(document.body).on('change',
        'input[type=hidden].editlive',
        formFieldHandler);

    $(document.body).on('click',
            'input[type=checkbox].editlive', function(event) {
        var $this = $(this),
            action = $(this).data('action'),
            attribute = $this.data('attribute');

        if (!action)
            return;

        editLive(action, $this.data('attribute'),
            $this.attr('checked') ? true : false);
    });

    $(document.body).on('click', 'a.editlive', function(event) {
        event.stopPropagation();
        event.preventDefault();

        var $this = $(this),
            action = $(this).data('action'),
            value = $this.data('value'),
            original = $this.data('original');

        if (!action || value == original)
            return;

        editLive(action, $this.data('attribute'), value);
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

        $form.on('change', 'input[type=checkbox]', function(event) {
            editLive(action, this.name, this.checked);
        });
    });
})(jQuery);
