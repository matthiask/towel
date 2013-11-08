;(function($) {
    var updateLive = function(data, context) {
        var context = $(context || document.body);

        $.each(data, function(key, value) {
            if (key == '!redirect') {
                window.location.href = value;
                return false;
            } else if (key == '!reload') {
                window.location.reload();
                return false;
            } else if (key == '!form-errors') {
                context.find('small.error').remove();
                context.find('.error').removeClass('error');

                if (!value)
                    return;

                $.each(value, function(key, value) {
                    var error = $('<small class="error"/>'),
                        field = $('#id_' + key),
                        container = field.closest('.field-' + key);

                    if (value) {
                        for (var i=0; i<value.length; ++i)
                            error.append(value[i] + '<br>');
                        field.after(error);
                        container.addClass('error');
                    }
                });

                return;
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

        initializeForms();
    };
    if (!window.updateLive) window.updateLive = updateLive;

    var editLive = function(action, attribute, value, callback, context) {
        var data = {};
        data[attribute] = value;

        $.post(action, data, function(data) {
            if (typeof(data) == 'string') {
                alert(data);
            } else {
                updateLive(data, context);
            }

            if (callback) {
                callback();
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

        editLive(action, $this.data('attribute'), this.value, function() {
            $this.trigger('editLive', [$this]);
        });
    }

    $(document.body).on('focusout',
        'input.editlive, textarea.editlive',
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
            $this.prop('checked') ? true : false,
            function() {
                $this.trigger('editLive', [$this]);
            });
    });

    $(document.body).on('click', 'a.editlive, li.editlive', function(event) {
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

    var initializeForms = function() {
        $('form.editlive').not('.initialized').each(function() {
            var $form = $(this),
                prefix = $form.data('form-prefix') || '',
                action = $form.attr('action');

            $form.on('submit', false);
            $form.addClass('initialized');
            $form.on('change', 'input, textarea, select',
                function(event) {
                    var source = $(this),
                        name = this.name;
                    if (this.tagName.toLowerCase() == 'input'
                            && source.attr('type') == 'checkbox') {
                        var source = $(this),
                            name = this.name;
                        if (prefix)
                            name = name.replace(prefix, '');
                        editLive(action, name, this.checked, function() {
                            source.trigger('editLive', [source]);
                        }, $form);
                    } else {
                        if (prefix)
                            name = name.replace(prefix, '');
                        editLive(action, name, this.value, function() {
                            source.trigger('editLive', [source]);
                        }, $form);
                    }
                });
        });
    };
    initializeForms();
})(jQuery);
