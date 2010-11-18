from django import template


register = template.Library()


@register.simple_tag
def batch_checkbox(form, id):
    cb = u'<input type="checkbox" name="batch_%s" value="%s" class="batch" %s/>'

    if id in form.ids:
        return cb % (id, id, 'checked="checked" ')

    return cb % (id, id, '')
