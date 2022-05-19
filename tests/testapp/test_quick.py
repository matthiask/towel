import re
from datetime import date, timedelta

from django.test import TestCase
from testapp.models import Person

from towel import quick


QUICK_RULES = [
    (re.compile(r"!!"), quick.static(important=True)),
    (
        re.compile(r"@(?P<family_name>\w+)"),
        quick.model_mapper(Person.objects.filter(is_active=True), "assigned_to"),
    ),
    (
        re.compile(r"\^\+(?P<due>\d+)"),
        lambda v: {"due": date.today() + timedelta(days=int(v["due"]))},
    ),
    (re.compile(r"\^(?P<due>[^\s]+)"), quick.due_mapper("due")),
    (re.compile(r"=(?P<estimated_hours>[\d\.]+)h"), quick.identity()),
    (
        re.compile(r"relationship:\((?P<value>[^\)]*)\)"),
        quick.model_choices_mapper(Person.RELATIONSHIP_CHOICES, "relationship"),
    ),
]


class QuickTest(TestCase):
    def test_parse_quickadd(self):
        data, rest = quick.parse_quickadd("", QUICK_RULES)
        self.assertEqual(list(data.items()), [])
        self.assertEqual(rest, [])

        data, rest = quick.parse_quickadd("!! do this do that", QUICK_RULES)
        self.assertEqual(list(data.items()), [("important", True)])
        self.assertEqual(" ".join(rest), "do this do that")

        p_muster = Person.objects.create(family_name="Muster")
        Person.objects.create(family_name="Blaa")
        Person.objects.create()
        data, rest = quick.parse_quickadd("@Muster Phone call !!", QUICK_RULES)
        self.assertEqual(data["assigned_to"], p_muster.pk)
        self.assertEqual(data["assigned_to_"], p_muster)
        self.assertEqual(data["important"], True)
        self.assertEqual(rest, ["Phone", "call"])

        data, rest = quick.parse_quickadd("@Unknown Phone", QUICK_RULES)
        self.assertTrue("assigned_to" not in data)
        self.assertEqual(rest, ["Phone"])
        # XXX Stop dropping unknowns?

        self.assertEqual(
            quick.parse_quickadd("^+3", QUICK_RULES)[0]["due"],
            date.today() + timedelta(days=3),
        )
        self.assertEqual(
            quick.parse_quickadd("^+42", QUICK_RULES)[0]["due"],
            date.today() + timedelta(days=42),
        )
        self.assertEqual(
            quick.parse_quickadd("^Today", QUICK_RULES)[0]["due"],
            date.today() + timedelta(days=0),
        )
        self.assertEqual(
            quick.parse_quickadd("^Tomorrow", QUICK_RULES)[0]["due"],
            date.today() + timedelta(days=1),
        )
        for name in "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday," "Sunday".split(
            ","
        ):
            due = quick.parse_quickadd("^%s" % name, QUICK_RULES)[0]["due"]
            self.assertTrue(date.today() <= due < date.today() + timedelta(days=7))

        self.assertEqual(
            quick.parse_quickadd("=0.3h", QUICK_RULES)[0]["estimated_hours"],
            "0.3",
        )
        self.assertEqual(
            quick.parse_quickadd("=10.3h", QUICK_RULES)[0]["estimated_hours"],
            "10.3",
        )
        self.assertEqual(
            quick.parse_quickadd("=37h", QUICK_RULES)[0]["estimated_hours"],
            "37",
        )

        self.assertEqual(
            quick.parse_quickadd("relationship:(unspecified)", QUICK_RULES)[0][
                "relationship"
            ],
            "",
        )
        self.assertEqual(
            quick.parse_quickadd("relationship:(married)", QUICK_RULES)[0][
                "relationship"
            ],
            "married",
        )
        self.assertEqual(
            quick.parse_quickadd("relationship:(in a relationship)", QUICK_RULES)[0][
                "relationship"
            ],
            "relation",
        )
        self.assertTrue(
            "relation"
            not in quick.parse_quickadd("relationship:(stupidity)", QUICK_RULES)[0]
        )
