from __future__ import absolute_import, unicode_literals

import httplib

from django.contrib.messages.api import get_messages

from towel.api import Resource, APIException


class FrankenResource(Resource):
    """
    Really ugly and hacky way of reusing customizations made in a ``ModelView``
    subclass for API resources. Reuses the following aspects of the
    ``ModelView`` instance:

    - Basic queryset filtering, i.e. ``get_query_set``
    - Form handling and saving, i.e. ``get_form``, ``get_form_instance``,
      ``save_form``, ``save_model`` and ``post_save``
    - Permissions management, i.e. ``adding_allowed``, ``editing_allowed``,
      ``deletion_allowed``
    """

    #: ``ModelView`` instance used for providing permissions and write
    #: access to the exposed model
    modelview = None

    def get_query_set(self):
        return self.modelview.get_query_set(self.request)

    def post_list(self, request, *args, **kwargs):
        """
        POST handler. Only supports full creation of objects by posting to
        the listing endpoint currently.
        """
        if not self.modelview.adding_allowed(request):
            raise APIException(status=httplib.FORBIDDEN)

        form_class = self.modelview.get_form(
            request,
            change=False)
        form = self.modelview.get_form_instance(
            request,
            form_class=form_class,
            change=False)

        try:
            is_valid = form.is_valid()
        except TypeError as exc:
            # This can happen when POSTing something of type
            # application/json with a list instead of a single entry,
            # e.g. {"customer_id": ["1"]}
            raise APIException('Malformed data', data={
                'exception': '%s' % exc})

        if not is_valid:
            raise APIException(data={
                'validation': form.errors,
            })

        instance = self.modelview.save_form(request, form, change=False)
        self.modelview.save_model(request, instance, form, change=False)
        self.modelview.post_save(request, instance, form, {}, change=False)

        data = self.api.serialize_instance(
            instance,
            build_absolute_uri=request.build_absolute_uri)
        return self.serialize_response(
            data,
            status=httplib.CREATED,
            headers={'Location': data['__uri__']})

    def put_detail(self, request, *args, **kwargs):
        """
        PUT handler. Only supports update of existing resources. Sets are not
        supported.

        You are required to provide the full set of fields, otherwise
        validation fails. If you are looking for partial updates, have a look
        at PATCH.
        """
        instance = self.detail_object_or_404()

        if not self.modelview.editing_allowed(request, instance):
            raise APIException(status=httplib.FORBIDDEN)

        # The ModelView code only does the right thing when method is POST
        request.method = 'POST'

        form_class = self.modelview.get_form(
            request,
            instance=instance,
            change=True)
        form = self.modelview.get_form_instance(
            request,
            form_class=form_class,
            instance=instance,
            change=True)

        if not form.is_valid():
            raise APIException(data={
                'validation': form.errors,
            })

        instance = self.modelview.save_form(request, form, change=True)
        self.modelview.save_model(request, instance, form, change=True)
        self.modelview.post_save(request, instance, form, {}, change=True)

        data = self.api.serialize_instance(
            instance, build_absolute_uri=request.build_absolute_uri)
        return self.serialize_response(data, status=httplib.OK)

    def patch_detail(self, request, *args, **kwargs):
        """
        PATCH handler. Only supports update of existing resources.

        This handler offloads the work to the PUT handler. It starts with the
        serialized representation from the database, overwrites values using
        the data from the PATCH request and calls PUT afterwards.
        """
        instance = self.detail_object_or_404()

        if not self.modelview.editing_allowed(request, instance):
            raise APIException(status=httplib.FORBIDDEN)

        data = self.api.serialize_instance(
            instance, build_absolute_uri=request.build_absolute_uri)
        for key in request.POST:
            if isinstance(data[key], (list, tuple)):
                data[key] = request.POST.getlist(key)
            else:
                data[key] = request.POST[key]
        request.POST = data

        return self.put_detail(request, *args, **kwargs)

    def delete_detail(self, request, *args, **kwargs):
        """
        DELETE handler. Only supports deletion of single items at the moment.
        """
        instance = self.detail_object_or_404()

        if not self.modelview.deletion_allowed(request, instance):
            raise APIException(status=httplib.FORBIDDEN, data={
                'messages': [{
                    'message': '%s' % msg,
                    'tags': msg.tags,
                } for msg in get_messages(request)],
            })

        instance.delete()
        return self.serialize_response({}, status=httplib.NO_CONTENT)
