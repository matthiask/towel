function towel_add_subform(slug) {
    var total_forms = $('#id_' + slug + '-TOTAL_FORMS');
    var new_id = parseInt(total_forms.val());

    total_forms.val(new_id + 1);
    var form = $('#' + slug + '-empty').clone(true);
    form.removeClass('empty').attr('id', slug + '-' + new_id);

    var attributes = ['id', 'name', 'for'];
    for (var i=0; i<attributes.length; ++i) {
        var attr = attributes[i];

        form.find('*[' + attr + '*=__prefix__]').each(function() {
            var el = $(this);
            el.attr(attr, el.attr(attr).replace(/__prefix__/, new_id));
        });
    }

    if (form[0].tagName.toLowerCase() == 'tr')
        form.appendTo('#' + slug + '-formset table').hide().fadeIn();
    else if (form[0].tagName.toLowerCase() == 'div')
        form.insertBefore('#' + slug + '-formset div.buttons').hide().fadeIn();

    return false;
}
