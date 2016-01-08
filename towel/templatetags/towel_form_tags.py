from __future__ import absolute_import, unicode_literals

from django import forms, template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


register = template.Library()


def _type_class(item):
    if isinstance(item.field.widget, forms.CheckboxInput):
        return 'checkbox'
    elif isinstance(item.field.widget, forms.DateInput):
        return 'date'
    elif isinstance(item.field.widget, forms.HiddenInput):
        return 'hidden'
    elif isinstance(
            item.field.widget,
            (forms.RadioSelect, forms.CheckboxSelectMultiple)):
        return 'list'
    elif isinstance(item.field.widget, forms.Select):
        return 'choice'
    return 'default'


@register.simple_tag
def form_items(form):
    """
    Render all form items::

        {% form_items form %}
    """
    return mark_safe(''.join(render_to_string('towel/_form_item.html', {
        'item': field,
        'is_checkbox': isinstance(field.field.widget, forms.CheckboxInput),
        'type_class': _type_class(field),
    }) for field in form if field.name != 'ignore_warnings'))


@register.inclusion_tag('towel/_form_item.html')
def form_item(item, additional_classes=None):
    """
    Helper for easy displaying of form items:

    ::

        {% for field in form %}
            {% form_item field %}
        {% endfor %}
    """

    return {
        'item': item,
        'additional_classes': additional_classes,
        'is_checkbox': isinstance(item.field.widget, forms.CheckboxInput),
        'type_class': _type_class(item),
    }


@register.inclusion_tag('towel/_form_item_plain.html')
def form_item_plain(item, additional_classes=None):
    """
    Helper for easy displaying of form items without any additional
    tags (table cells or paragraphs) or labels::

        {% form_item_plain field %}
    """

    return {
        'item': item,
        'additional_classes': additional_classes,
        'is_checkbox': isinstance(item.field.widget, forms.CheckboxInput),
        'type_class': _type_class(item),
    }


@register.tag
def form_errors(parser, token):
    """
    Show all form and formset errors::

        {% form_errors form formset1 formset2 %}

    Silently ignores non-existant variables.
    """

    tokens = token.split_contents()

    return FormErrorsNode(*tokens[1:])


class FormErrorsNode(template.Node):
    def __init__(self, *items):
        self.items = [template.Variable(item) for item in items]

    def render(self, context):
        items = []
        for item in self.items:
            try:
                var = item.resolve(context)
                if isinstance(var, dict):
                    items.extend(var.values())
                elif isinstance(var, (list, tuple)):
                    items.extend(var)
                else:
                    items.append(var)
            except template.VariableDoesNotExist:
                # We do not care too much
                pass

        errors = False
        has_non_field_errors = False

        form_list = []
        formset_list = []

        for i in items:
            if isinstance(i, forms.BaseForm):
                form_list.append(i)
            else:
                formset_list.append(i)

            if getattr(i, 'non_field_errors', lambda: None)():
                errors = True
                has_non_field_errors = True
            if getattr(i, 'errors', None):
                errors = True

        if not errors:
            return ''

        return render_to_string('towel/_form_errors.html', {
            'forms': form_list,
            'formsets': formset_list,
            'errors': errors,
            'has_non_field_errors': has_non_field_errors,
        })


@register.tag
def form_warnings(parser, token):
    """
    Show all form and formset warnings::

        {% form_warnings form formset1 formset2 %}

    Silently ignores non-existant variables.
    """

    tokens = token.split_contents()

    return FormWarningsNode(*tokens[1:])


class FormWarningsNode(template.Node):
    def __init__(self, *items):
        self.items = [template.Variable(item) for item in items]

    def render(self, context):
        items = []
        for item in self.items:
            try:
                var = item.resolve(context)
                if isinstance(var, dict):
                    items.extend(var.values())
                elif isinstance(var, (list, tuple)):
                    items.extend(var)
                else:
                    items.append(var)
            except template.VariableDoesNotExist:
                # We do not care too much
                pass

        warnings = False

        form_list = []
        formset_list = []

        for i in items:
            if isinstance(i, forms.BaseForm):
                form_list.append(i)
                if getattr(i, 'warnings', None):
                    warnings = True
            else:
                formset_list.append(i)
                if any(getattr(f, 'warnings', None) for f in i):
                    warnings = True

        if not warnings:
            return ''

        return render_to_string('towel/_form_warnings.html', {
            'forms': form_list,
            'formsets': formset_list,
            'warnings': True,
        })


@register.tag
def dynamic_formset(parser, token):
    """
    Implements formsets where subforms can be added using the
    ``towel_add_subform`` javascript method::

        {% dynamic_formset formset "activities" %}
            ... form code
        {% enddynamic_formset %}
    """

    tokens = token.split_contents()
    nodelist = parser.parse(('enddynamic_formset',))
    parser.delete_first_token()

    return DynamicFormsetNode(tokens[1], tokens[2], nodelist)


class DynamicFormsetNode(template.Node):
    def __init__(self, formset, slug, nodelist):
        self.formset = template.Variable(formset)
        self.slug = template.Variable(slug)
        self.nodelist = nodelist

    def render(self, context):
        formset = self.formset.resolve(context)
        slug = self.slug.resolve(context)

        result = []

        context.update({
            'empty': True,
            'form_id': '%s-empty' % slug,
            'form': formset.empty_form,
        })
        result.append('<script type="text/template" id="%s-empty">' % slug)
        result.append(self.nodelist.render(context))
        result.append('</script>')
        context.pop()

        for idx, form in enumerate(formset.forms):
            context.update({
                'empty': False,
                'form_id': '%s-%s' % (slug, idx),
                'form': form,
            })
            result.append(self.nodelist.render(context))
            context.pop()

        return mark_safe(''.join(result))
