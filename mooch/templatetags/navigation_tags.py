from django import template
import re

register = template.Library()

class_matcher = re.compile('(class="[^"]+)(")')
tag_matcher = re.compile(r'<([a-z0-9]+)([ >])')

def mark_current(navigation, current):
    current_tokens = current.split('/')
    tokens = []

    low = 1
    if len(current_tokens)>2:
        low = 2

    for i in range(low, len(current_tokens)):
        tokens.append(re.escape('/'.join(current_tokens[0:i])+'/'))

    current_matcher = re.compile('href="(' + '|'.join(tokens) + ')"')

    lines = navigation.splitlines()
    out = []
    for line in lines:
        if current_matcher.search(line):
            if class_matcher.search(line):
                out.append(class_matcher.sub(r'\1 mark\2', line))
            else:
                out.append(tag_matcher.sub(r'<\1 class="mark"\2', line))
        else:
            out.append(line)

    return '\n'.join(out)

def do_mark_current(parser, token):
    try:
        tag_name, url_variable = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires one argument" % token.contents.split()[0]

    nodelist = parser.parse(('endmark_current',))
    parser.delete_first_token()
    return MarkCurrentNode(nodelist, url_variable)

class MarkCurrentNode(template.Node):
    def __init__(self, nodelist, url_variable):
        self.nodelist = nodelist
        self.url_variable = template.Variable(url_variable)

    def render(self, context):
        output = self.nodelist.render(context)
        return mark_current(output, self.url_variable.resolve(context))

register.tag('mark_current', do_mark_current)
