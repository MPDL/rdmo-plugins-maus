import base64
import zipfile
from io import BytesIO

import requests

from django.template import TemplateSyntaxError
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import get_language, override
from django.utils.translation import gettext_lazy as _

from rdmo.core.utils import render_to_format
from rdmo.domain.models import Attribute
from rdmo.projects.utils import get_value_path
from rdmo.views.models import View

def zip(content_files):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(
        file=zip_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zip_archive:
        for name, file_content in content_files.items():
            zip_archive.writestr(zinfo_or_arcname=name, data=file_content)

    zip_buffer.seek(0)

    return zip_buffer

def unzip(zip_buffer):
    content_files = {}
    with zipfile.ZipFile(zip_buffer) as zip:
        for name in zip.namelist():
            with zip.open(name) as file:
                content = file.read()
                content_files[name] = content

    return content_files

def get_licenses(spdx_ids):
    # https://github.com/spdx/license-list-data    
    license_contents = {}
    for id in spdx_ids:
        url = 'https://api.github.com/repos/spdx/license-list-data/contents/text/{spdx_id}.txt'.format(spdx_id=id)        
        response = requests.get(url, headers={'Accept': 'application/vnd.github+json'})
        try:
            response.raise_for_status()
            base64_string_of_content = response.json().get('content')
            base64_bytes_of_content = base64_string_of_content.encode('utf-8')
            content_bytes = base64.b64decode(base64_bytes_of_content)
            content = content_bytes.decode('utf-8')
            license_contents[f'LICENSE_{id.replace("-", "_")}'] = content
        except:
            continue
        
    return license_contents

def get_project_license_ids(project, snapshot=None):
    attribute = Attribute.objects.get(uri='https://rdmorganiser.github.io/terms/domain/smp/software-license')
    spdx_ids = [license.value for license in project.values.filter(snapshot=snapshot, attribute=attribute)]
    spdx_ids = [id.removeprefix('Other Software License: ').removeprefix('Andere Software-Lizenz: ') for id in spdx_ids]
    return spdx_ids

def render_to_license(request, project, snapshot=None, choice=None):
        spdx_ids = get_project_license_ids(project, snapshot)
        
        if len(spdx_ids) == 0: # no license(s) selected yet
            return render(request, 'core/error.html', {
                'title': _('Something went wrong'),
                'errors': [_('No license(s) selected yet for this project.')]
            }, status=200)
        
        if choice is not None:
            spdx_id = next((l for l in spdx_ids if l.lower().replace('-', '_') == choice), choice)
            spdx_ids = [spdx_id]
        
        license_contents = get_licenses(spdx_ids)
        if len(license_contents) == 1:
            content = list(license_contents.values())[0]
            content_type = 'text/plain'
            file_name = 'LICENSE'
            content_disposition = f'attachment; filename="{file_name}"'

        elif len(license_contents) > 1:
            content = zip(license_contents)
            content_type = 'application/zip'
            file_name = 'licenses.zip'
            content_disposition = f'attachment; filename="{file_name}"'

        else:
            return None
        
        response = HttpResponse(
            content,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": content_disposition,
            },
        )
        return response

def render_from_view(request, project, snapshot, view_uri, title, export_format, language_code=None):
    language = language_code if language_code is not None else get_language()
    with override(language):
        view = View.objects.get(uri=view_uri)

        try:
            rendered_view = view.render(project, snapshot)
        except TemplateSyntaxError:
            return None

        response = render_to_format(
            None, export_format, title, 'projects/project_view_export.html', {
            'format': export_format,
            'title': title,
            'view': view,
            'rendered_view': rendered_view,
            'resource_path': get_value_path(project, snapshot)
            }
        )
        response['Content-Disposition'] = f'attachment; filename="{title}"'

        return response