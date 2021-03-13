"""
Generate Terraform for the Azure Policies
"""
import os
import logging
import click
from click_option_group import optgroup, RequiredMutuallyExclusiveOptionGroup
from azure_guardrails import set_log_level
from azure_guardrails.terraform.terraform import TerraformTemplateNoParams, TerraformTemplateWithParams
from azure_guardrails.shared import utils, validate
from azure_guardrails.scrapers.compliance_data import ComplianceCoverage
from azure_guardrails.shared.config import get_default_config, get_config_from_file
from azure_guardrails.guardrails.services import ServicesV2

logger = logging.getLogger(__name__)

supported_services_argument_values = utils.get_service_names()
supported_services_argument_values.append("all")


@click.command(name="generate-terraform", short_help="")
@optgroup.group("Azure Policy selection", help="")
@optgroup.option(
    "--service",
    "-s",
    type=str,
    # type=click.Choice(supported_services_argument_values),
    required=True,
    default="all",
    help="Services supported by Azure Policy definitions. Set to 'all' for all policies",
    callback=validate.click_validate_supported_azure_service,
)
@optgroup.option(
    "--exclude-services",
    "exclude_services",
    type=str,
    help="Exclude specific services (comma-separated) without using a config file.",
    callback=validate.click_validate_comma_separated_excluded_services
)
@optgroup.option(
    "--enforce",
    "-e",
    "enforcement_mode",
    is_flag=True,
    default=False,
    help="Deny bad actions instead of auditing them.",
)
@optgroup.group("Configuration", help="")
@optgroup.option(
    "--config-file",
    "-c",
    "config_file",
    type=click.Path(exists=False),
    required=False,
    help="The config file",
)
@optgroup.group(
    "Parameter Options",
    cls=RequiredMutuallyExclusiveOptionGroup,
    help="",
)
@optgroup.option(
    "--no-params",
    is_flag=True,
    default=False,
    help="Only generate policies that do NOT require parameters",
)
@optgroup.option(
    "--params-optional",
    is_flag=True,
    default=False,
    help="Only generate policies where parameters are OPTIONAL",
)
@optgroup.option(
    "--params-required",
    is_flag=True,
    default=False,
    help="Only generate policies where parameters are REQUIRED",
)
# Mutually exclusive option groups
# https://github.com/click-contrib/click-option-group
# https://stackoverflow.com/questions/37310718/mutually-exclusive-option-groups-in-python-click
@optgroup.group(
    "Policy Scope Targets",
    cls=RequiredMutuallyExclusiveOptionGroup,
    help="",
)
@optgroup.option(
    "--subscription",
    type=str,
    help="The name of a subscription. Supply either this or --management-group",
)
@optgroup.option(
    "--management-group",
    type=str,
    help="The name of a management group. Supply either this or --subscription",
)
@optgroup.group(
    "Other options",
    help="",
)
@optgroup.option(
    "--no-summary",
    "-n",
    is_flag=True,
    default=False,
    help="Do not generate markdown or CSV summary files associated with the Terraform output",
)
@click.option(
    "-v",
    "--verbose",
    "verbosity",
    count=True,
)
def generate_terraform(
        service: str,
        exclude_services: list,
        config_file: str,
        no_params: bool,
        params_optional: bool,
        params_required: bool,
        subscription: str,
        management_group: str,
        enforcement_mode: bool,
        no_summary: bool,
        verbosity: int
):
    """
    Get Azure Policies
    """
    set_log_level(verbosity)

    if not config_file:
        logger.info(
            "You did not supply an config file. Consider creating one to exclude different policies. We will use the default one.")
        config = get_default_config(exclude_services=exclude_services)
    else:
        config = get_config_from_file(config_file=config_file, exclude_services=exclude_services)

    if subscription:
        management_group = ""
    else:
        subscription = ""

    summary_file_prefix = ""
    if no_params:
        summary_file_prefix = "no-params"
    elif params_required:
        summary_file_prefix = "params-required"
    elif params_optional:
        summary_file_prefix = "params-optional"

    if service == "all":
        services = ServicesV2(config=config)
    else:
        services = ServicesV2(service_names=[service], config=config)

    if no_params:
        display_names = services.get_display_names_sorted_by_service_no_params()
        display_names_list = services.display_names_no_params
        terraform_template = TerraformTemplateNoParams(policy_names=display_names,
                                                       subscription_name=subscription,
                                                       management_group=management_group,
                                                       enforcement_mode=enforcement_mode)
    else:
        display_names = services.get_display_names_sorted_by_service_with_params(params_required=params_required)

        if params_required:
            display_names_list = services.display_names_params_required
        else:
            display_names_list = services.display_names_params_optional

        terraform_template = TerraformTemplateWithParams(parameters=display_names,
                                                         subscription_name=subscription,
                                                         management_group=management_group,
                                                         enforcement_mode=enforcement_mode)
    result = terraform_template.rendered()
    print(result)

    if not no_summary:
        compliance_coverage = ComplianceCoverage(display_names=display_names_list)
        if subscription:
            target_name = subscription
        else:
            target_name = management_group
        summary_file_prefix = f"{summary_file_prefix}-{service}-table-{target_name}"

        # Write Markdown summary
        markdown_table = compliance_coverage.markdown_table()
        markdown_file = f"{summary_file_prefix}.md"
        if os.path.exists(markdown_file):
            if verbosity >= 1:
                utils.print_grey(f"Removing the previous file: {markdown_file}")
            os.remove(markdown_file)
        with open(markdown_file, "w") as f:
            f.write(markdown_table)

        if verbosity >= 1:
            utils.print_grey(f"CSV file written to: {markdown_file}")

        # Write CSV summary
        csv_file = f"{summary_file_prefix}.csv"
        compliance_coverage.csv_table(csv_file, verbosity=verbosity)
