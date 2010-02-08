from django import template

register = template.Library()


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
def form_item_plain(item, additional_classes=None):
    """
    Helper for easy displaying of form items.
    """

    return {
        'item': item,
        'additional_classes': additional_classes,
        }
