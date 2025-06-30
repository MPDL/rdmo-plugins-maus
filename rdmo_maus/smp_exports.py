
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from rdmo.projects.exports import Export

from .utils import get_project_license_ids, render_from_view, render_to_license

class SMPExportMixin:
    smp_exports_map = {
        'readme': {
            'form_choice_label': 'README',
            'form_choice_file_path': 'README.md',
            'render_function': render_from_view,
            'render_function_kwargs': {
                'view_uri': 'https://rdmo.mpdl.mpg.de/terms/views/smp-readme',
                'title': 'README.md',
                'export_format': 'markdown'
            }
        },
        'citation': {
            'form_choice_label': 'CITATION',
            'form_choice_file_path': 'CITATION.cff',
            'render_function': render_from_view,
            'render_function_kwargs': {
                'view_uri': 'https://rdmo.mpdl.mpg.de/terms/views/smp-citation',
                'title': 'CITATION.cff',
                'export_format': 'plain'
            }
        },
        'license': {
            'form_choice_label': 'LICENSE',
            'form_choice_file_path': 'LICENSE',
            'render_function': render_to_license,
            'render_function_kwargs': {}
        }
    }

    @property
    def smp_exports(self):
        # Add smp specific export choices if project has SMP Catalog
        smp_exports = {}
        if self.project.catalog.uri_path == 'smp':
            for k, v in self.smp_exports_map.items():
                if k == 'license':
                    license_ids = get_project_license_ids(self.project, self.snapshot)
                    license_count = len(license_ids)
                    if license_count == 1:
                        k = f'license_{license_ids[0].lower().replace("-", "_")}'
                    elif license_count > 1:
                        license_exports = {
                            f'license_{l.lower().replace("-", "_")}': {
                                'label': f'LICENSE_{l.replace("-", "_")}', 
                                'file_path': f'LICENSE_{l.replace("-", "_")}'
                            }
                            for l in license_ids
                        }
                        smp_exports.update(license_exports)
                        continue
                    else:
                        continue

                smp_exports[k] = {'label': v['form_choice_label'], 'file_path': v['form_choice_file_path']}

        return smp_exports

    def render_smp_export(self, choice):
        if choice.startswith('license'):
            form_choice_label, form_choice_file_path, render_function, kwargs = self.smp_exports_map['license'].values()
            kwargs['choice'] = choice.replace('license_', '')
        else:
            form_choice_label, form_choice_file_path, render_function, kwargs = self.smp_exports_map[choice].values()
        
        response = render_function(self.project, self.snapshot, **kwargs)
        return response
    
class SMPReadmeExport(SMPExportMixin, Export):
    def render(self):
        if self.project.catalog.uri_path != 'smp':
            return render(self.request, 'core/error.html', {
                'title': _('SMP-specific Plugin'),
                'errors': [_('This plugin only works for projects with the Software Management Plan catalogue')]
            }, status=200)
        
        response = self.render_smp_export('readme')

        if response is None:
            return render(self.request, 'core/error.html', {
                'title': _('Something went wrong'),
                'errors': [_('Export format could not be created')]
            }, status=200)

        filename = self.smp_exports_map['readme']['render_function_kwargs']['title']
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
    
class SMPCitationExport(SMPExportMixin, Export):
    def render(self):
        if self.project.catalog.uri_path != 'smp':
            return render(self.request, 'core/error.html', {
                'title': _('SMP-specific Plugin'),
                'errors': [_('This plugin only works for projects with the Software Management Plan catalogue')]
            }, status=200)

        response = self.render_smp_export('citation')

        if response is None:
            return render(self.request, 'core/error.html', {
                'title': _('Something went wrong'),
                'errors': [_('Export format could not be created')]
            }, status=200)

        filename = self.smp_exports_map['citation']['render_function_kwargs']['title']
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
    
class SMPLicenseExport(SMPExportMixin, Export):
    def render(self):
        if self.project.catalog.uri_path != 'smp':
            return render(self.request, 'core/error.html', {
                'title': _('SMP-specific Plugin'),
                'errors': [_('This plugin only works for projects with the Software Management Plan catalogue')]
            }, status=200)

        response = render_to_license(self.project, self.snapshot)

        if response is None:
            return render(self.request, 'core/error.html', {
                'title': _('Something went wrong'),
                'errors': [_('Export format could not be created')]
            }, status=200)
        
        return response