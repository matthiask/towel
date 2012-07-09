import httplib
import json
from urllib import urlencode

from django.contrib.messages.api import get_messages
from django.forms.models import model_to_dict

from towel.api import Resource, APIException


class FrankenResource(Resource):
    """
    Really ugly and hacky way of reusing customizations made in a ``ModelView``
    subclass for API resources.
    """

    #: ``ModelView`` instance used for providing permissions and write
    #: access to the exposed model
    modelview = None

    def get_query_set(self):
        return self.modelview.get_query_set(self.request)

    def unserialize_request(self):
        if self.request.META.get('CONTENT_TYPE') == 'application/json':
            # XXX HACK ALARM
            #self.request.POST = QueryDict(urlencode(json.loads(
            #    self.request.body)))
            setattr(
                self.request,
                self.request.method,
                json.loads(self.request.body),
                )

        # Thanks piston and tastypie
        if self.request.method not in ('PUT', 'PATCH'):
            return

        request, method = self.request, self.request.method

        if hasattr(request, '_post'):
            del request._post
            del request._files

        request.method = 'POST'
        request._load_post_and_files()
        request.method = method
        setattr(request, method, request.POST)

    def post(self, request, *args, **kwargs):
        objects = self.objects()
        if objects.single or objects.set:
            raise APIException(status=httplib.NOT_IMPLEMENTED)

        form_class = self.modelview.get_form(request,
            instance=objects.single,
            change=False,
            )
        form = self.modelview.get_form_instance(request,
            form_class=form_class,
            instance=objects.single,
            change=False,
            )

        try:
            is_valid = form.is_valid()
        except TypeError as e:
            # This can happen when POSTing something of type
            # application/json with a list instead of a single entry,
            # e.g. {"customer_id": ["1"]}
            raise APIException('Malformed data', data={
                'exception': unicode(e),
                })

        if not is_valid:
            raise APIException(data={
                'validation': form.errors,
                })

        instance = self.modelview.save_form(request, form, change=False)
        self.modelview.save_model(request, instance, form, change=False)
        self.modelview.post_save(request, instance, form, {}, change=False)

        data = self.api.serialize_instance(instance,
            build_absolute_uri=request.build_absolute_uri,
            )
        return self.serialize_response(data, status=httplib.CREATED, headers={
            'Location': data['__uri__'],
            })

    def patch(self, request, *args, **kwargs):
        objects = self.objects()
        if not objects.single:
            raise APIException(status=httplib.NOT_IMPLEMENTED)

        data = request.PATCH.copy()
        for key, value in model_to_dict(objects.single).items():
            if key not in data:
                data[key] = value

        form_class = self.modelview.get_form(request,
            instance=objects.single,
            change=True,
            )
        # XXX extend_args_if_post does of course NOT work... because
        # method == 'PATCH'
        form = self.modelview.get_form_instance(request,
            form_class=form_class,
            instance=objects.single,
            change=True,
            )

        print 'asasd'
        print form.is_valid()
        print form.errors
        print form.non_field_errors()

        print unicode(form).encode('utf-8')

        if not form.is_valid():
            raise APIException(data={
                'validation': form.errors,
                })

        instance = self.modelview.save_form(request, form, change=True)
        self.modelview.save_model(request, instance, form, change=True)
        self.modelview.post_save(request, instance, form, {}, change=True)

        data = self.api.serialize_instance(instance,
            build_absolute_uri=request.build_absolute_uri,
            )
        return self.serialize_response(data, status=httplib.OK)

    def delete(self, request, *args, **kwargs):
        objects = self.objects()
        if not objects.single:
            raise APIException(status=httplib.NOT_IMPLEMENTED)

        if not self.modelview.deletion_allowed(request, objects.single):
            raise APIException(status=httplib.FORBIDDEN, data={
                'messages': [{
                    'message': unicode(msg),
                    'tags': msg.tags,
                    } for msg in get_messages(request)],
                })

        objects.single.delete()
        return self.serialize_response({}, status=httplib.NO_CONTENT)
