from django import template
from django.forms import BaseForm
from django.template.loader import render_to_string


register = template.Library()


@register.simple_tag
def form_items(form):
    return u''.join(render_to_string('_form_item.html', {'item': field}) for field in form)


@register.inclusion_tag('_form_item.html')
def form_item(item, additional_classes=None):
    """
    Helper for easy displaying of form items.
    """

    return {
        'item': item,
        'additional_classes': additional_classes,
        }


@register.inclusion_tag('_form_item_plain.html')
def form_item_plain(item):
    """
    Helper for easy displaying of form items.
    """

    return {
        'item': item,
        }


@register.tag
def form_errors(parser, token):
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

        form_list = []
        formset_list = []

        for i in items:
            if isinstance(i, BaseForm):
                form_list.append(i)
            else:
                formset_list.append(i)

            if getattr(i, 'errors', None) or getattr(i, 'non_field_errors', lambda:None)():
                errors = True

        if not errors:
            return u''

        return render_to_string('_form_errors.html', {
            'forms': form_list,
            'formsets': formset_list,
            'errors': True,
            })


@register.tag
def dynamic_formset(parser, token):
    """
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

        context.push()
        context['empty'] = True
        context['form_id'] = '%s-empty' % slug
        context['form'] = formset.empty_form
        result.append(self.nodelist.render(context))
        context['empty'] = False

        for idx, form in enumerate(formset.forms):
            context['form_id'] = '%s-%s' % (slug, idx)
            context['form'] = form
            result.append(self.nodelist.render(context))

        context.pop()
        return u''.join(result)
