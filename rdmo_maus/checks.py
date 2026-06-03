from django.conf import settings
from django.core.checks import Error, register


@register()
def check_export_format_settings(app_configs, **kwargs):
    errors = []

    export_formats = settings.EXPORT_FORMATS
    try:
        next(format for format in export_formats if format[0] == 'plain')
    except StopIteration:
        errors.append(
            Error(
                'settings.EXPORT_FORMATS does not contain format "plain".',
                hint='Add `("plain", _("Plain Text"))` to EXPORT_FORMATS in config/settings/local.py'
            )
        )

    return errors
