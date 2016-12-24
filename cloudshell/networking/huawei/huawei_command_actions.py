import re
from cloudshell.cli.cli_exception import CliException
from cloudshell.networking.huawei.command_templates.huawei_configure_vlan_template import *
from cloudshell.networking.huawei.command_templates.huawei_commands_templates import *



def install_firmware(config_session, logger, firmware_file_name):
    """Set boot firmware file.
    :param config_session: current config session
    :param logger:  logger
    :param firmware_file_name: firmware file name
    """
    config_session.send_command(**UPDATE_FIRMWARE.get_command(firmware_file_name))


def create_vlan(session, logger, vlan_range, action_map=None, error_map=None):
    """Create vlan entity on the device

    :param session: current session
    :param logger:  logger
    :param vlan_range: range of vlans to be created
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    """
    ranges_list = []
    is_range = True if '-' in vlan_range else False
    splited_vlan_range = vlan_range.split(',')

    if (len(splited_vlan_range) > 1) or is_range:
        for vlan in splited_vlan_range:

            if '-' in vlan:
                ranges_leafs = vlan.split('-')

                if (int(ranges_leafs[0]) > int(ranges_leafs[1])):
                    temp = ranges_leafs[0]
                    ranges_leafs[0] = ranges_leafs[1]
                    ranges_leafs[1] = temp

                ranges_list = ranges_list + (range(int(ranges_leafs[0]), int(ranges_leafs[1]) + 1))
            else:
                ranges_list.append(vlan)

            session.send_command(**VLAN_BATCH.get_command(vlan_id=ranges_leafs[0] + " to " + ranges_leafs[1],
                                                              action_map=action_map,
                                                              error_map=error_map))
    else:
        session.send_command(**CONFIGURE_VLAN.get_command(vlan_id=vlan_range,
                                                          action_map=action_map,
                                                          error_map=error_map))

def set_vlan_to_interface(config_session, logger, vlan_range, port_mode, port_name, qnq, c_tag,
                          does_require_single_switchport_cmd=False,
                          action_map=None,
                          error_map=None):
    """Assign vlan to a certain interface

    :param config_session: current config session
    :param logger:  logger
    :param vlan_range: range of vlans to be assigned
    :param port_mode: switchport mode
    :param port_name: interface name
    :param qnq: qinq settings (dot1q tunnel)
    :param c_tag: selective qnq
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    """

    curr_config = config_session.send_command(**DISPLAY_RUNNING.get_command(interface=port_name))
    clean_current_configuration_on_interface(config_session, logger, curr_config, port_name, action_map=None,
                                             error_map=None)
    config_session.send_command(**CONFIGURE_INTERFACE.get_command(port_name=port_name))
    config_session.send_command(**UNDO_SHUTDOWN.get_command(action_map=action_map, error_map=error_map))
    config_session.send_command(**START_PORT_MODE.get_command(action_map=action_map, error_map=error_map))

    is_range = True if '-' in vlan_range else False

    if port_mode == 'trunk':
        if (is_range):
            splited_vlan_range = vlan_range.split(',')

            if (len(splited_vlan_range) > 1) or is_range:
                for vlan in splited_vlan_range:

                    if '-' in vlan:
                        ranges_leafs = vlan.split('-')

                        if (int(ranges_leafs[0]) > int(ranges_leafs[1])):
                            temp = ranges_leafs[0]
                            ranges_leafs[0] = ranges_leafs[1]
                            ranges_leafs[1] = temp

                        ranges_list = ranges_list + (range(int(ranges_leafs[0]), int(ranges_leafs[1]) + 1))
                    else:
                        ranges_list.append(vlan)

                        config_session.send_command(**ALLOW_TRUNK_VLAN.get_command(vlan_id=ranges_leafs[0] + " to " + ranges_leafs[1],
                                                                  action_map=action_map,
                                                                  error_map=error_map))

        else:
            config_session.send_command(
                **ALLOW_TRUNK_VLAN.get_command(vlan_id=vlan_range,
                                               action_map=action_map,
                                               error_map=error_map))
    elif 'access' in port_mode and vlan_range != '':
        if not qnq or qnq is False:
            logger.info('qnq is {0}'.format(qnq))
            config_session.send_command(
                **PORT_MODE_ACCESS.get_command(vlan_id=vlan_range,
                                               action_map=action_map,
                                               error_map=error_map))
            config_session.send_command(
                **PORT_DEFAULT_VLAN.get_command(vlan_id=vlan_range,
                                               action_map=action_map,
                                               error_map=error_map))

    if qnq and qnq is True:
        config_session.send_command(
            **QNQ.get_command(vlan_id=vlan_range,
                                            action_map=action_map,
                                            error_map=error_map))
        config_session.send_command(
            **PORT_DEFAULT_VLAN.get_command(vlan_id=vlan_range,
                                            action_map=action_map,
                                            error_map=error_map))

    config_session.send_command(
        **COMMIT.get_command(action_map=action_map,
                                        error_map=error_map))

    logger.info('Vlan configuration completed\n')

def clean_current_configuration_on_interface(config_session, logger, current_config, port_name, action_map=None,
                                      error_map=None):

        """

        :param :
        :return: success message
        :rtype: string
        """

        action_map = {'[\[\(][Yy]es/[Nn]o[\)\]]|\[Continue\]|Continue?\[Y/N\]': lambda session: session.send_line('yes'),
                        '[\[\(][Yy]/[Nn][\)\]]': lambda session: session.send_line('y')}
        for line in current_config.splitlines():
            if re.search('^\s*port default vlan\s+|^\s*port link-type\s+|^\s*port trunk allow-pass vlan\s+', line):
                if(not re.search('^\s*port trunk allow-pass vlan\s+', line)):
                    line_to_remove = re.sub('\s+\d+[-\d+,]+|trunk|access', '', line)
                if not line_to_remove:
                    line_to_remove = line

                config_session.send_command(
                    **UNDO.get_command(command=line_to_remove.strip(' '), action_map=action_map, error_map=error_map))

        return 'Finished configuration of ethernet interface!'

def reload_device(session, logger, timeout, action_map=None, error_map=None):
    """Reload device

    :param session: current session
    :param logger:  logger
    :param timeout: session reconnect timeout
    """

    try:
        session.send_command(**RELOAD.get_command(action_map=action_map, error_map=error_map))
    except Exception as e:
        logger.info("Device rebooted, starting reconnect")
    session.reconnect(timeout)



def copy(session, logger, source, destination, vrf=None, action_map=None, error_map=None):
    """Copy file from device to tftp or vice versa, as well as copying inside devices filesystem.

    :param session: current session 
    :param logger:  logger
    :param source: source file
    :param destination: destination file
    :param vrf: vrf management name
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    :raise Exception: 
    """

    if not vrf:
        vrf = None
    output = session.send_command(
        **COPY.get_command(src=source, dst=destination, vrf=vrf, action_map=action_map, error_map=error_map))

    status_match = re.search(r'\d+ bytes copied|copied.*[\[\(].*[0-9]* bytes.*[\)\]]|[Cc]opy complete', output,
                             re.IGNORECASE)
    if not status_match:
        match_error = re.search('%.*|TFTP put operation failed.*|sysmgr.*not supported.*\n', output, re.IGNORECASE)
        message = 'Copy Command failed. '
        if match_error:
            logger.error(message)
            message += re.sub('^%|\\n', '', match_error.group())
        else:
            error_match = re.search(r"error.*\n|fail.*\n", output, re.IGNORECASE)
            if error_match:
                logger.error(message)
                message += error_match.group()
        raise Exception('Copy', message)


def get_current_interface_config(session, logger, port_name, action_map=None, error_map=None):
    """Retrieve current interface configuration

    :param session: current session 
    :param logger:  logger
    :param port_name: 
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    :return: str
    """

    return session.send_command(
        **DISPLAY_RUNNING.get_command(port_name=port_name, action_map=action_map, error_map=error_map))


def get_current_boot_config(session, action_map=None, error_map=None):
    """Retrieve current boot configuration

    :param session: current session 
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    :return: 
    """

    return session.send_command(**SHOW_RUNNING.get_command(boot='', action_map=action_map, error_map=error_map))


def get_current_os_version(session, action_map=None, error_map=None):
    """Retrieve os version

    :param session: current session 
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    :return: 
    """

    return session.send_command(**DISPLAY_VERSION.get_command(action_map=action_map, error_map=error_map))



def clean_interface_switchport_config(config_session, logger, current_config, port_name, action_map=None,
                                      error_map=None):
    """Remove current switchport configuration from interface

    :param config_session: current config session
    :param logger:  logger
    :param current_config: current interface configuration
    :param port_name: interface name
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    """

    logger.debug("Start cleaning interface switchport configuration")
    config_session.send_command(**CONFIGURE_INTERFACE.get_command(port_name=port_name))
    for line in current_config.splitlines():
        if line.strip(" ").startswith('switchport '):
            config_session.send_command(
                **UNDO.get_command(command=line.strip(' '), action_map=action_map, error_map=error_map))

    logger.debug("Completed cleaning interface switchport configuration")


def remove_port_configuration_commands(session, config_to_remove, action_map=None, error_map=None):
    """Remove current interface switchport configuration

    :param session: current session 
    :param config_to_remove: current interface configuration,
        will be used to extract switchport config and remove it one by one
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    """

    for line in config_to_remove.splitlines():
        if line.strip(" ").startswith('switchport '):
            session.send_command(
                **NO.get_command(command=line.strip(' '), action_map=action_map, error_map=error_map))


def delete_file(session, logger, path, action_map=None, error_map=None):
    """Delete file on the device

    :param session: current session 
    :param logger:  logger
    :param path: path to file
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    """

    session.send_command(**DEL.get_command(target=path, action_map=action_map, error_map=error_map))


def verify_interface_configured(vlan_range, current_config):
    """Verify interface configuration

    :param vlan_range: 
    :param current_config: 
    :return: True or False
    """

    return str(vlan_range) in current_config


def override_running(session, path, action_map=None, error_map=None):
    """Override running-config

    :param session: current session current cli session
    :param path: relative path to the file on the remote host tftp://server/sourcefile
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    :raise Exception:
    """

    conf_replace = CONFIGURE_REPLACE.get_command(path=path, action_map=action_map, error_map=error_map)
    output = session.send_command(**conf_replace)
    match_error = re.search(r'[Ee]rror.*$', output)
    if match_error:
        error_str = match_error.group()
        raise Exception('Override_Running', 'Configure replace completed with error: ' + error_str)


def enable_snmp(session, snmp_community, action_map=None, error_map=None):
    """Enable SNMP on the device

    :param session: current session 
    :param snmp_community: community name
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    """
    session.send_command(**SNMP_ENABLE.get_command(action_map=action_map, error_map=error_map))


def disable_snmp(session, snmp_community, action_map=None, error_map=None):
    """Disable SNMP on the device

    :param session: current session 
    :param snmp_community: community name
    :param action_map: actions will be taken during executing commands, i.e. handles yes/no prompts
    :param error_map: errors will be raised during executing commands, i.e. handles Invalid Commands errors
    """
    session.send_command(**SNMP_DISABLE.get_command(action_map=action_map, error_map=error_map))


def get_port_name(logger, port):
    """Get port name from port resource full address

    :param port: port resource full address (192.168.1.1/0/34)
    :return: port name (FastEthernet0/23)
    :rtype: string
    """

    if not port:
        err_msg = 'Failed to get port name.'
        logger.error(err_msg)
        raise Exception('HuaweiConnectivityOperations: get_port_name', err_msg)

    temp_port_name = port.split('/')[-1]
    if 'port-channel' not in temp_port_name.lower():
        temp_port_name = temp_port_name.replace('-', '/')

    logger.info('Interface name validation OK, portname = {0}'.format(temp_port_name))
    return temp_port_name
