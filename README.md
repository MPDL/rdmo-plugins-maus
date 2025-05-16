# rdmo-plugins-maus

This repo implements three plugins for Software Management Plan (SMP) projects in [RDMO](https://github.com/rdmorganiser/rdmo):

* a README export plugin, which creates a README.md file with the data in an SMP project
* a CITATION export plugin, which creates a CITATION.cff file with the data in an SMP project
* a LICENSE export plugin, which creates a LICENSE file or a licenses.zip file with the license(s) chosen for an SMP project

This repo also implements an SMPExportMixin, which can be used by other [export plugins](https://rdmo.readthedocs.io/en/latest/plugins/#project-export-plugins). This SMPExportMixin offers a list of SMP-specific export options and their content. An example implementation is the [GitLabExportProvider](https://github.com/MPDL/rdmo-plugins-gitlab/tree/dev).


## Setup

1. Install the plugin in your RDMO virtual environment using pip (directly from GitHub):

```bash
pip install git+https://github.com/MPDL/rdmo-plugins-maus
```

2. For the export plugins, add the plugins to PROJECT_EXPORTS in config/settings/local.py:

```python
PROJECT_EXPORTS += [
    ('readme', _('README'), 'rdmo_maus.smp_exports.SMPReadmeExport'),
    ('citation', _('CITATION'), 'rdmo_maus.smp_exports.SMPCitationExport'),
    ('license', _('LICENSE'), 'rdmo_maus.smp_exports.SMPLicenseExport'),
]
```

3. For the README and CITATION export plugins, import the views needed in your RDMO instance. The views are "view-smp-citation.xml" and "view-smp-readme.xml" and can be found in our [forked rdmo-catalog repo](https://github.com/MPDL/rdmo-catalog/tree/MPG-catalogues/rdmorganiser/views)

4. [Optional] These plugins are SMP-specific, and do not work properly for other catalogues. If a user clicks on one of them, they will be informed that the plugin only works for SMP projects. However, with the following adaptations, these plugins will only be shown to the user if the project has an SMP catalogue:

4.1 Add these lines in `rdmo.core.settings.py`:

```python
SETTINGS_EXPORT += ['SMP_PROJECT_EXPORTS']

SMP_PROJECT_EXPORTS = []
```

4.2 Modify this part of the code in `rdmo.projects.templates.projects.project_detail_sidebar.html`:

```html
{% has_perm 'projects.export_project_object' request.user project as can_export_project %}
{% if settings.PROJECT_EXPORTS and can_export_project %}
<h2 id="export-project">{% trans 'Export' %}</h2>

<ul class="list-unstyled">
    {% for key, label, class in settings.PROJECT_EXPORTS %}
    {% if key not in settings.SMP_PROJECT_EXPORTS or project.catalog.uri_path == 'smp' %} # !!! NEW LINE !!!
    <li>
        <a href="{% url 'project_export' project.pk key %}" target="_blank">
            {{ label }}
        </a>
    </li>
    {% endif %} # !!! NEW LINE !!!
    {% endfor %}
</ul>
{% endif %}
```

4.3 Add the export plugin keys to SMP_PROJECT_EXPORTS in `config/settings/local.py`:

```python
SMP_PROJECT_EXPORTS += ['readme', 'citation', 'license']
```

## Usage

### Export plugins

For SMP projects, users can export custom files (README, CITATION, LICENSE) created with the SMP project's data.

### SMPExportMixin

This repo also implements an SMPExportMixin, which can be used by other [export plugins](https://rdmo.readthedocs.io/en/latest/plugins/#project-export-plugins). This SMPExportMixin offers a list of SMP-specific export options (README, CITATION, LICENSE) and their content. An example implementation is the [GitLabExportProvider](https://github.com/MPDL/rdmo-plugins-gitlab/tree/dev).