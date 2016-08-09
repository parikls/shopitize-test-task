from album.models import Album


class TemplatesAlbumContext:

    def process_template_response(self, request, response):
        """
        Add albums to template context if some
        errors occurred during view processing
        """
        if response.template_name == "index.html":
            if not response.context_data.get("albums"):
                response.context_data["albums"] = Album.objects.to_dict_all()
        return response

