
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override 

from rdmo.projects.exports import Export
from rdmo import __version__

from .mixins import SMPExportMixin

class SMPBaseLocalExport(SMPExportMixin, Export):
    def _render(self, choice):
        if self.project.catalog.uri_path != 'smp':
            return render(self.request, 'core/error.html', {
                'title': _('SMP-specific Plugin'),
                'errors': [_('This plugin only works for projects with the Software Management Plan catalogue')]
            }, status=200)
        
        response = self.render_smp_export(choice)

        if response is None:
            return render(self.request, 'core/error.html', {
                'title': _('Something went wrong'),
                'errors': [_('Export choice could not be created')]
            }, status=200)

        return response
    
class SMPReportExport(SMPBaseLocalExport):
    def render(self):
        # SMP Report is only available in English, 
        # so translate all selected options if translation available
        with override('en'):
            return self._render('report')

class SMPReadmeExport(SMPBaseLocalExport):
    def render(self):
        return self._render('readme')
    
class SMPCitationExport(SMPBaseLocalExport):
    def render(self):
        return self._render('citation')
    
class SMPLicenseExport(SMPBaseLocalExport):
    def render(self):
        return self._render('licenses')