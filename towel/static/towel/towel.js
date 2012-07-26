;function addInlineForm(slug, onComplete) {
    var totalForms = $('#id_' + slug + '-TOTAL_FORMS'),
        newId = parseInt(totalForms.val());

    totalForms.val(newId + 1);
    var empty = $('#' + slug + '-empty'),
        attributes = ['id', 'name', 'for'],
        form = $(empty.html());

    form.removeClass('empty').attr('id', slug + '-' + newId);

    for (var i=0; i<attributes.length; ++i) {
        var attr = attributes[i];

        form.find('*[' + attr + '*=__prefix__]').each(function() {
            var el = $(this);
            el.attr(attr, el.attr(attr).replace(/__prefix__/, newId));
        });
    }

    // insert the form after the last sibling with the same tagName
    // cannot use siblings() here, because the empty element may be the
    // only one (if no objects exist until now)
    form.insertAfter(
        empty.parent().children('[id|=' + slug + ']:last')
        ).hide().fadeIn();

    if (onComplete)
        onComplete(form);

    return false;
};

// backwards compat
window.towel_add_subform = addInlineForm;
