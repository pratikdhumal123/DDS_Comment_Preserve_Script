



## dragon data



The Cisco ACI physical topology is based on a spine-leaf architecture, where each leaf switch connects to every spine switch, forming a bipartite graph with no direct leaf-to-leaf or spine-to-spine connections. Leaf switches serve as the connection points for servers, storage, physical or virtual service devices, and external networks, while spine switches provide high-speed forwarding between leaf nodes. This design supports scalability, high bandwidth, and redundancy, and is managed centrally by the Cisco Application Policy Infrastructure Controller (APIC) to automate fabric discovery and configuration.


mastart is here now you can see. The latter is used by the APIC to reference specific devices for configuration purposes. The following devices are installed in %%customerName's ACI solution:

<caption name="ACI-FABRIC-NAME - Hardware Components">

| Node ID | Node Name | Role | Model | Serial Number | Location | Room | Rack |
| --- | --- | --- | --- | --- | --- | --- | --- |

</caption>




### Fabric Connectivity



The following figure de
picts the overall physical topology of the ACI solution.


<caption name="Physical Topology Overview">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Physical_Topology_Overview.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### Leaf and Spine Connectivity



The table below summarizes the spine-to-leaf connections.

<caption name="Infrastructure Physical Connections">

| Device A | Port A | Transceiver A | Device B | Port B | Transceiver B | Cable Type | Connector Type | Comment |
|---|---|---|---|---|---|---|---|---|
| No cabling data found - please populate docascode.tech.shared.cabling.groups with name 'fabric-links' | | | | | | | | |

</caption>

The IaC Data Model for ACI formally defines the format of the data input files. This is an example of how the ACI switches must be defined in the input files:

<caption name="Leaf and Spine Registration Data Model">

```yaml
apic:
  node_policies:
    nodes:
      - id: 101
        pod: 1
        role: leaf
        serial_number: [node-serial-number]
        name: Leaf-101
      - id: 1001
        pod: 1
        role: spine
        serial_number: [node-serial-number]
        name: Spine-1001
```
</caption>

For further information on how the ACI switches are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/node_policies/node_registration/).



### APIC Connectivity



The following figure depicts the APIC connectivity pattern to the ACI fabric.


<caption name="APIC Connectivity Pattern">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/APIC_Connectivity_Pattern.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


Each APIC has an Eth2/1, and Eth2/2 port connected to different leaf switches. The APIC forms a bond0 interface across these ports for redundancy. Ports being bonded are not working as active/active but in active/standby mode. Only one of two ports is actively communicating with the fabric.

The following tables contain the specific APIC connectivity allocations.

<caption name="APIC Connections">

| Device A | Port A | Transceiver A | Device B | Port B | Transceiver B | Cable Type | Connector Type | Comment |
|---|---|---|---|---|---|---|---|---|
| No cabling data found - please populate docascode.tech.shared.cabling.groups with name 'apic-connections' | | | | | | | | |

</caption>


<caption name="APIC Connections Physical Topology">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/APIC_Connections_Physical_Topology.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### Remote Leaf Connectivity





<caption name="Remote Leaf connections">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Remote_Leaf_connections.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### FEX Connectivity





<caption name="Fabric Extender Connections">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Fabric_Extender_Connections.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### External Connectivity



The following figure depicts the physical connectivity between fabric border leaf switches and external devices (switches, routers, firewalls, etc.).


<caption name="External Connectivity Overview">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/External_Connectivity_Overview.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### Firewall/Load Balancer Connectivity



The table below summarizes external connections to firewalls and load balancers.

<caption name="External Firewall/Load Balancer Connections">

| Device A | Port A | Transceiver A | Device B | Port B | Transceiver B | Cable Type | Connector Type | Comment |
|---|---|---|---|---|---|---|---|---|
| No cabling data found - please populate docascode.tech.shared.cabling.groups with name 'external-firewall-lb' | | | | | | | | |

</caption>




### Routers Connectivity



The table below summarizes external routed connections.

<caption name="External Router Connections">

| Device A | Port A | Transceiver A | Device B | Port B | Transceiver B | Cable Type | Connector Type | Comment |
|---|---|---|---|---|---|---|---|---|
| No cabling data found - please populate docascode.tech.shared.cabling.groups with name 'external-routers' | | | | | | | | |

</caption>


<caption name="External Router Connections Topology">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/External_Router_Connections_Topology.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### Switches Connectivity



The table below summarizes external switches connections.

<caption name="External Switch Connections">

| Device A | Port A | Transceiver A | Device B | Port B | Transceiver B | Cable Type | Connector Type | Comment |
|---|---|---|---|---|---|---|---|---|
| No cabling data found - please populate docascode.tech.shared.cabling.groups with name 'external-switches' | | | | | | | | |

</caption>


<caption name="External Switch Connections Topology">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/External_Switch_Connections_Topology.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### Server Connectivity




<caption name="Server Connections">

| Device A | Port A | Transceiver A | Device B | Port B | Transceiver B | Cable Type | Connector Type | Comment |
|---|---|---|---|---|---|---|---|---|
| No cabling data found - please populate docascode.tech.shared.cabling.groups with name 'server-connections' | | | | | | | | |

</caption>




### IPN/ISN Connectivity





<caption name="IPN Connections Topology">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/IPN_Connections_Topology.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### Out-of-band Management Connectivity





<caption name="OOB Connections Topology">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/OOB_Connections_Topology.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>





# Fabric Setup







## APIC Setup



During the Fabric Initial configuration, a set of values are required. These values are:

<caption name="APIC initial setup parameters">

| Parameters | Description |
| --- | --- |
| Fabric Name | Fabric Domain Name |
| Fabric ID | Fabric ID |
| Number of Controllers in the fabric | APIC Cluster Size (This number does not include the standby controller if used) |
| POD ID | POD ID the APIC controller belongs to |
| Standby Controller | Yes, if configuring the standby controller, No otherwise |
| Controller ID | Unique ID number for the APIC instance (this is the APIC node ID) |
| TEP Pool | TEP Pool range for the POD 1 |
| VLAN ID infra network | Infrastructure VLAN ID |
| Bridge domain multicast address Pool GIPo | IP address used for the Fabric Multicast (Assigned to the different bridge domains).\nThe prefix length must be a /15\nThe valid ranges are 225.0.0.0/15 to 231.254.0.0/15\nThe default range is 225.0.0.0/15 |
| IPv4/Ipv6 address for OOB management | APIC Controller OOB Management IP |
| IPv4/Ipv6 address of the default gateway | APIC Controller OOB Default Gateway |
| Admin password | Local Admin password (only asked during the setup of the first APIC controller) |
</caption>

The following design decisions have been made in this section:

<tip name="Design Decision DD.001">
Fabric ID 1 will be used for the ACI fabric.
<br><br>
Rationale: Cisco best practice recommends using Fabric ID 1 as the standard default. Deviations are only required in very specific and uncommon circumstances, and using the default simplifies operations and avoids potential compatibility issues.
</tip>
<br><br>




### Fabric Name and ID



- Each ACI fabric is configured with a Fabric Domain. During the initial configuration of each APIC, the dialogue asks for the Fabric Name to be specified. This Fabric Name is the Fabric Domain. Do not be confused by the difference in terminology; they are the same thing.
- The Fabric Domain specified must be identical for all APICs that will form a cluster (i.e., that will be part of the same fabric). It is a good practice for different ACI fabrics to be given different Fabric Names.
- At the present time, the recommendation is to specify 1 as the Fabric ID for all ACI Fabrics, except in very specific circumstances, which do not apply for this deployment.

Following naming convention will be used for Fabric: ACI-[Location]-[n]

<caption name="Fabric Location Fabric ID Fabric Name">

| Fabric Location | Fabric ID | Fabric Name |
| --- | --- | --- |
</caption>

Having completed the physical installation of the ACI equipment, the ACI fabric build can begin starting with the day-0 setup. This includes the initial configuration of the first APIC, completing the fabric discovery, configuring the switch node management interfaces, joining the other APICs to the controller cluster and finally performing software/firmware upgrades to the target release identified for the deployment.

In order to complete the basic set-up, it is necessary to define the values that will be assigned to a number of configuration parameters. This section provides a description of those parameters. It does not include a complete record of all parameters, but it will provide summary information (e.g., value ranges, or a subset of values as examples).



### TEP Pool Range



Each node in the fabric will get a set of IP addresses assigned from the TEP pool range defined during the initial fabric set-up.

The IPs will be assigned as follows:

- Loopback addresses
- PTEP - Physical Tunnel End Point, assigned to all the nodes
- vPC TEP - a TEP address to represent the vPC
- FTEP - Fabric Tunnel End Point, one for the entire fabric
- Proxy-TEP - Proxy Tunnel End Point, assigned to a set of spines, proxy-TEP the MAC addresses, for IPv4, for IPv6

Each link between the leaf nodes and spines has a sub-interface and an IP address on this sub-interface and each host that sends VXLAN tagged traffic will use a TEP address also (AVS/AVE with VXLAN, Hyper-V, Openstack, Remote Leaf). Uniqueness of the ACI TEP pool address space is a requirement on use cases where the ACI overlay is extended outside the ACI Fabric. The following are some scenarios where this would occur:

- Multi-Pod
- Multi-Site
- Hyper-V VMM Integration
- Remote Leaf
- Openstack Integration

In these scenarios, the TEP pool subnet will be visible to the wider network, and depending on the routing design of the wider network it may be globally routable. Even if none of the above scenarios apply, which is the case for this deployment, future changes may result in one or more of them being applicable. Should this occur, it is not possible to change the TEP pool without completely rebuilding the ACI Fabric, which is very disruptive.

- The smallest TEP pool that can be configured is /19.
- Since re-configuring TEP pool requires a fabric re-build, the safest long-term pool size must be chosen.
- For Large ACI deployment (more than 1000 edge ports, more than 20 Leaf Switches) it is safest to use a /16 TEP pool.
- For Medium ACI deployments (up to 1000 edge ports, 20 Leaf switches) a /20 TEP pool may fit the purpose.

In the %%customerName ACI design, this will be the TEP pool approach:

<caption name="TEP Pool Definitions">

| Fabric | Pod ID | TEP Pool Range |
| --- | --- | --- |
</caption>

The following design decisions have been made in this section:

<tip name="Design Decision DD.002">
The TEP pool allocated to each ACI fabric will be unique across the entire network and will not overlap with address space allocated elsewhere.
<br><br>
Rationale: Cisco strongly recommends TEP pool uniqueness because the TEP pool subnet becomes visible to the wider network in multi-pod, multi-site, GOLF/L3EVPN, AVS/AVE, Remote Leaf, and OpenStack scenarios. Since the TEP pool cannot be changed without a complete fabric rebuild, ensuring uniqueness from day one prevents costly and disruptive re-addressing in the future.
</tip>
<br><br>




### Infrastructure VLAN



Communication between the APIC and the devices forming the Fabric (Leaf, Spine, AVS, etc) happens via the Infrastructure VLAN, and more specifically on the Infrastructure tenant in the Overlay-1 VRF. The Infrastructure VLAN is the encapsulation used for that communication. The Infra VLAN is chosen at the time of the fabric bring-up and cannot be changed without erasing the fabric.

Although the Infrastructure VLAN is not meant to be stretched outside of the fabric, there are use cases where this can happen, for instance usage of Cisco AVS/AVE or integration with Openstack Compute node. We therefore recommend to choose an unused and not reserved VLAN to avoid any conflicts.

In the %%customerName ACI design, this will be the Infrastructure VLAN:

<caption name="Infra VLAN">

| Fabric | Infra VLAN |
| --- | --- |
| ACI-FABRIC-NAME | N/A |
</caption>



### Bridge Domain Multicast Address Pool - GIPO



The ACI Fabric requires a pool of class D IPv4 addresses for internal use, and during the initial configuration dialogue it is necessary to specify a range of addresses (a /15 range) for this purpose.

In case the same IPN needs to be shared across sites, then the TEP pools as well as the Multicast bridge domain (BD) GIPo pool should be unique across sites.



### Additional Info per APIC



The following tables show the parameters for each one of the APIC servers in the fabric:

<caption name="ACI-FABRIC-NAME - Node OOB IP address OOB Def GW">

| Node | OOB IP address | OOB Def GW | Node Type |
| --- | --- | --- | --- |

</caption>




## OOB Setup



Configure OOB IP address and verify pre-set values according to the following table:

<caption name="ACI-FABRIC-NAME - Node OOB IP address OOB Def GW">

| Node | OOB IP address | OOB Def GW | Node Type |
| --- | --- | --- | --- |

</caption>




### CIMC Firmware Version



The recommended CIMC firmware releases for APIC servers are:

<caption name="Server platform APIC version CIMC version">

| Server platform | APIC version | CIMC version |
| --- | --- | --- |
| C220/C240 M5 (APIC-L3/M3) | 5.2(x) | 4.2(3e) |
| C220/C240 M5 (APIC-L3/M3) | 6.0(3) | 4.2(3e) |
| C225 M6 (APIC-L4/M4) | 6.0(3) | 4.2(3e) |

</caption>

The IaC Data Model for ACI formally defines the format of the data input files. This is an example of how APIC nodes must be defined in the input files:

<caption name="Node Registration Data Model">

```yaml
apic:
  node_policies:
    nodes:
      - id: 1
        role: apic
        serial_number: [node-serial-number]
        name: APIC-1
        oob_address: 10.0.0.11
        oob_gateway: 10.0.0.1
      - id: 2
        role: apic
        serial_number: [node-serial-number]
        name: APIC-2
        oob_address: 10.0.0.12
        oob_gateway: 10.0.0.1
      - id: 3
        role: apic
        serial_number: [node-serial-number]
        name: APIC-3
        oob_address: 10.0.0.13
        oob_gateway: 10.0.0.1
```
</caption>

For further information on how APIC nodes are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/node_policies/node_registration/).



### CIMC Access



After configuring the CIMC IP addresses, verify connectivity to each APIC's CIMC interface:


<caption name="ACI-FABRIC-NAME - CIMC Access Information">

| Node | CIMC IP Address | HTTPS URL | Default Credentials |
| --- | --- | --- | --- |

</caption>

<warning>Change default CIMC credentials immediately after initial configuration for security purposes.</warning>





# Fabric Administration



This section will describe how administration services like External Data Collectors, Import/Export Policies and RBAC  are defined in the ACI fabric.



## AAA Setup



The chapter about AAA configuration describes the authentication, authorization, and accounting (AAA) services used to control access to network resources, enforce policies, and track usage for security and management purposes. It covers the processes of verifying user identity, granting access rights, and logging user activities, including configuration of AAA servers, server groups, and local database support on Cisco devices.



### Users Configuration







### Local Users




In order to create a local user, the following parameters need to be defined:

<caption name="ACI-FABRIC-NAME - Local User">

| Username | First Name | Last Name | Email | Phone | Description | Status |
| --- | --- | --- | --- | --- | --- | --- |
</caption>

User security attributes also need to be specified.

<caption name="ACI-FABRIC-NAME - User Security Attributes">

| Username | Expires | Expire Date | Certificate Name |
| --- | --- | --- | --- |
</caption>

For each security domain, Users' Roles need to be configured.

<caption name="ACI-FABRIC-NAME - User's Roles">

| Username | Security Domain | Role | Privilege Type |
| --- | --- | --- | --- |
</caption>

For a list of Roles and associated Privileges, please refer to Cisco APIC Security Configuration Guide.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Local Users must be defined in the input files:

<caption name="Local Users Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      users:
        - username: user1
          password: ciscocisco
          domains:
            - name: all
              roles:
                - name: admin
                  privilege_type: write
            - name: common
```
</caption>

For further information on how the Local Users are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/user/).



### Remote Users




To configure a remote user authenticated through an external authentication provider, you must meet the following prerequisites:

- The DNS configuration should have already been resolved with the hostname of the authentication provider server.
- You must configure the management subnet.



### Cisco AV Pair




The Cisco APIC requires that an administrator configure a Cisco AV Pair on an external authentication server. To do so, an administrator adds a Cisco AV pair to the existing user record. The Cisco AV pair specifies the APIC required RBAC roles and privileges for the user. The Cisco AV Pair format is the same for RADIUS, LDAP, or TACACS+.

The Cisco AV pair format is as follows:

<caption name="ACI-FABRIC-NAME - Cisco AV Pair Format">

| Parameter | Description | Example |
| --- | --- | --- |
| shell:domains | Security domain assignment | shell:domains=all/admin/ |
| shell:domains | Multiple domain roles | shell:domains=domainA/admin/domainB/read-all/ |
| shell:roles | Specific role assignment | shell:roles=admin |
</caption>

<caption name="ACI-FABRIC-NAME - AAA Configuration Examples">

**Users with admin access to entire fabric:**

For users, whose authentication and credentials are managed on external servers, user ID for a Linux shell can be specified in cisco-av-pair.

**Users with read only access to fabric:**

<note name="Note">Read only users do not have access to leaves or spines, admin write privilege is required.</note>

**Users with admin access to tenants under security domain "mydomain" and read only access to the rest of tenants:**

</caption>




### Authentication







### AAA




AAA Authentication provides a way of identifying a user based on the username and password before the access to the system is granted.

AAA Authentication in ACI fabric defines the following default Authentication properties:

Remote user login policy:

The default role policy for the remote user with invalid (or no) CiscoAVPairs returned by the AAA server.

The options are:

- Assign Default Role
- No Login (default)

Default Authentication:

The default security method used for processing authentication requests and the associated Provider Group. The realm options are:

- Local (default)
- Radius
- Tacacs+
- LDAP
- RSA
- SAML

Console Authentication:

The security method to be used for processing authentication requests when accessing ACI switches from the console. The realm options are:

- Local (default)
- Radius
- Tacacs+
- LDAP
- RSA

<caption name="ACI-FABRIC-NAME - AAA Authentication">

| Remote User Login Policy | Default Authentication Realm | Console Authentication Realm |
| --- | --- | --- |
| no-login | local | local |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the AAA must be defined in the input files:

<caption name="AAA Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      remote_user_login_policy: no-login
      default_realm: local
      console_realm: tacacs
```
</caption>

For further information on how AAA is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/aaa/).



### Login Domains




A login domain defines the authentication mechanism (Local, TACACS+, RADIUS, LDAP, RSA, SAML) that will be used to authenticate a user. Login Domains can be used with all access methods (REST, CLI, GUI) and it must be specified during the authentication.

By default, the fallback domain is implemented, as its name implies, to fall back to the default local authentication in case a remote authentication is not available (e.g., all AAA servers time out).

<warning>Do not remove or reconfigure the fallback login domain. Doing so could result in being locked out from the system.</warning>

The named fallback domain is a preconfigured login domain that is used to define a backup authentication realm, which is typically a local realm.

It can be invoked in the event that the AAA providers that comprise the Default or Console Authentication Realm become unreachable or otherwise nonfunctional.

When the "fallback check" option is set to "false" (default), the fallback domain is always active.

When the "fallback check" option is set to "true" (Active if ICMP health check fails) and TACACS servers are reachable login via fallback is denied (apic:fallback\\admin).

When TACACS is not reachable, a user can authenticate via fallback: apic:fallback\\admin. The user in this case cannot log in by simply providing 'admin' as username.

The following domains are configured:

<caption name="ACI-FABRIC-NAME - Login Domains">

| Login Domain Name | Realm | Description | Auth Choice |
| --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Login Domains must be defined in the input files:

<caption name="Login Domains Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      login_domains:
      - name: tacacs
        realm: tacacs
        description: login domain tacacs
        tacacs_providers:
        - hostname_ip: 1.1.1.1
          priority: 1
      - name: radius
        realm: radius
        description: login domain radius
        radius_providers:
        - hostname_ip: 3.3.3.1
          priority: 1
      - name: ldap
        realm: ldap
        description: login domain ldap
        auth_choice: LdapGroupMap
        ldap_group_map: test-users-map
        ldap_providers:
        - hostname_ip: 2.2.2.2
          priority: 1
```
</caption>

For further information on how the Login Domains are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/login_domain/). Provider Groups are created in the LDAP/RADIUS/TACACS+ Management section and are used to define the authentication servers to be used for the specific protocol selected.



### LDAP




LDAP user authentication is the process of validating a username and password combination with a directory server such as Microsoft Active Directory. LDAP directories are standard technology for registering user, group, and permission information.

An LDAP group map rule can be configured. It is made up of security domain roles and is assigned to an LDAP group map. You choose the security domain(s), choose the role(s) to include in the LDAP group map rule, and specify read or write privileges for each role.

An LDAP group map contains LDAP group map rules and is used to configure LDAP servers without Cisco AVPairs.

LDAP authentication is deployed in the %%customerName environment.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the LDAP must be defined in the input files:

<caption name="LDAP Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      ldap:
        providers:
          - hostname_ip: 2.2.2.2
            description: descr
            port: 3389
            bind_dn: CN=testuser,OU=Employees,DC=example,DC=com
            base_dn: OU=Employees,DC=example,DC=com
            password: test@1234
            timeout: 10
            retries: 4
            enable_ssl: true
            filter: cn=$userid
            attribute: memberOf
            ssl_validation_level: permissive
            mgmt_epg: oob
            server_monitoring: true
            monitoring_username: user1
            monitoring_password: pass1
          - hostname_ip: 2.2.2.3
        group_map_rules:
          - name: test-users-rules
            description: descr
            group_dn: CN=test-users,DC=example,DC=com
            security_domains:
              - name: all
                roles:
                  - name: admin
                    privilege_type: write
              - name: common
        group_maps:
          - name: test-users-map
            rules:
              - name: test-users-rules
```
</caption>

For further information on how LDAP is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/ldap/).



### RADIUS




Remote Authentication Dial-In User Service is a networking protocol that provides Authentication, Authorization, and Accounting for users who connect and use a network service.

RADIUS authentication is deployed in the %%customerName environment.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the RADIUS must be defined in the input files:

<caption name="RADIUS Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      radius_providers:
        - hostname_ip: 1.1.1.1
          key: '123'
```
</caption>

For further information on how RADIUS is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/radius/).



### TACACS+




The AAA Authentication functionality in ACI fabric is achieved using TACACS+. Configuring AAA using TACACS+ authentication on ACI requires:

- Configuring one or more TACACS+ providers.
- Configuring a TACACS+ provider group.
- Configuring a login domain.
- Configuring the AAA Authentication policy to use the correct method for authentication.

<caption name="ACI-FABRIC-NAME - TACACS+ Providers">

| Hostname/IP | Port | Protocol | Timeout | Retries | Management EPG | Monitoring |
| --- | --- | --- | --- | --- | --- | --- |
</caption>

<caption name="ACI-FABRIC-NAME - TACACS+ Provider Group">

| Login Domain | Provider Hostname/IP | Priority |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the TACACS+ must be defined in the input files:

<caption name="TACACS+ Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      tacacs_providers:
      - hostname_ip: 1.1.1.1
        key: '123'
```
</caption>

For further information on how TACACS+ is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/tacacs/).



### Security







### Management Setting




Management setting defines a set of properties for specifying the level of password security. Configurable properties include enabling or disabling the password strength check feature, enabling or disabling the password change interval, specifying the length of the password change interval and the number of password changes permitted per interval, and specifying the length of time the GUI can remain idle before a user is required to log back in to the system.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Management Settings must be defined in the input files:

<caption name="Management Setting Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      management_settings:
        password_strength_check: true
        password_strength_profile:
        password_mininum_length: 8
        password_maximum_length: 64
        password_strength_test_type: default
        password_class_flags:
          - digits
          - lowercase
          - uppercase
        password_change_during_interval: true
        password_change_count: 2
        password_change_interval: 48
        password_no_change_interval: 24
        password_history_count: 5
        web_token_timeout: 600
        web_token_max_validity: 24
        web_session_idle_timeout: 1200
        include_refresh_session_records: true
        enable_login_block: false
        login_block_duration: 60
        login_max_failed_attempts: 5
        login_max_failed_attempts_window: 5
```
</caption>

For further information on how the Management Settings are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/aaa/).



### Security Domains




The Security Domains tab contains the options to create or delete a security domain and displays a summary table that lists your existing security domains.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Security Domains must be defined in the input files:

<caption name="Security Domains Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      security_domains:
        - name: SEC1
          restricted_rbac_domain: true
```
</caption>

For further information on how the Security Domains are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/aaa/).



### Roles




The Roles tab lists all the pre-configured roles and their privileges and it gives the option to configure customized roles.



### RBAC Rules




RBAC rules enable a fabric-wide administrator to provide access across security domains that would otherwise be blocked. Use RBAC rules to expose physical resources or share services that otherwise are inaccessible because they are in a different security domain. RBAC rules provide read access only to their target resources.



### Public Key Management




The Public Key Management tab provides the options to create or delete a key ring and displays a summary table that lists your existing key rings.

A keyring is necessary to create and hold an SSL certificate. The SSL certificate contains the public RSA key and signed identity information of a PKI device. The PKI device holds a pair of RSA encryption keys, one kept private and one made public, stored in an internal key ring. The keyring certificate merges into the PKI device keyring to create a trusted relationship.

A Certificate Authority (CA) trustpoint issues and validates (signs) digital certificates. When participating in secure communications using the public key infrastructure (PKI), a participant can verify the identity of the other party through the CA that signed the other party's public key.

The Certificate Authorities tab provides the options to create or delete a Certificate Authority (CA) and displays a summary table that lists your existing CAs.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Public Key Management must be defined in the input files:

<caption name="Public Key management Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      key_rings:
      - name: KEYRING1
        ca_certificate: CA1
        certificate: '-----BEGIN CERTIFICATE-----
          [Add certificate here]
          -----END CERTIFICATE-----

          '
        private_key: '-----BEGIN RSA PRIVATE KEY-----
         [Add private key here]
          -----END RSA PRIVATE KEY----- |'
```
</caption>

For further information on how Public Key Management is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/keyring/).



## ACI RBAC



The ACI Role-Based Access Control (RBAC) enables or restricts users access to ACI fabric configuration objects.

The ACI RBAC model is based on Roles, Privileges and Security Domains.

A User (local or remote) can be associated to:

- A set of roles
- For each role, a privilege type: no access, read-only, or read-write.
- One or more security domain tags that identify the portions of the management information tree (MIT) that a user can access.

A Role is a collection of privileges.

An ACI object is associated with specific privilege bits. As the example figure below shows, the Write Access and the Read Access privilege bits are associated to an EPG.


<caption name="Privilege Bits Associated to an EPG">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Privilege_Bits_Associated_to_an_EPG.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


Certain ACI objects can be configured to be associated to a Security Domain Tag. Users with matching tag can access that object.

**Privileges**

A privilege is a managed object that enables or restricts access to a particular function within the system. The ACI fabric manages access privileges at the managed object (MO) level. For example, fabric-equipment is a privilege bit. This bit is set by the Application Policy Infrastructure Controller (APIC) on all objects that correspond to equipment in the physical fabric.

The following figure provides an example of privilege-bits applied to a VRF (fvCtx Class):


<caption name="MO Privileges">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/MO_Privileges.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


In this figure, we see that an admin or tenant-connectivity-l3 are required to write to a VRF (fvCtx) Object. The "Read Access:" lists all the privileges which have read access to that VRF Class.

<info name="Info">The list of privileges which have read and write access to a specific class is available on the Class documentation page accessible through the object browser on the APIC GUI.</info>

**Role**

A role is a collection of privileges. For example, because an "admin" role is configured with privilege bits for "fabric-equipment" and "tenant-security," the "admin" role has access to all objects that correspond to equipment of the fabric and tenant security.

**Security Domain**

A security domain is a tag associated with a certain subtree in the ACI MIT object hierarchy. An administrator can configure a Security Domain tag and then assign it to these objects:

- Tenants
- Physical Domains
- L3 and L2 external Domains
- VMM Domains

Users assigned to the same security domain tag will have access to the MIT of those objects.

By default, the ACI fabric includes these pre-created domains:

- all - access to the entire MIT
- common
- mgmt



## Remote Collectors



In ACI, external data collectors can be configured to receive a variety of system data, SNMP, Syslog, TACACS, or Callhome destinations. Below sections describe the ACI setup for sending this data to the external collectors.



### SNMP Traps Collector



The SNMP protocol is used by network devices for management and monitoring. The most commonly used SNMP messages are SNMP traps which are alert messages used to report issues. ACI can be configured to send these kinds of SNMP Traps to an external SNMP Trap collector by defining SNMP monitoring destination groups.

<caption name="ACI-FABRIC-NAME - SNMP Traps Destination Group">


| Name | SNMP Trap Destination | Community |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the SNMP Trap Collector must be defined in the input files:

<caption name="SNMP Traps Collector Data Model">

```yaml
apic:
  fabric_policies:
    monitoring:
      snmp_traps:
        - name: TRAP1
          description: desc1
          destinations:
            - hostname_ip: 2.2.2.2
              port: 1062
              version: v3
              community: test
              security: priv
              mgmt_epg: inb
```
</caption>



For further information on how the SNMP Trap Collector is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/snmp_trap/).



### Syslog Collector



The Syslog protocol is used by network devices to send event messages to an external Syslog collector used for system management and security auditing. Syslog information regarding ACI can typically include logging data, alerts, or audit information. In ACI, Syslog messages can be sent to an external Syslog collector by configuring Syslog monitoring destination groups. Below tables provide further information.

<caption name="ACI-FABRIC-NAME - Syslog Monitoring Destination Group">

| Name | Format | Admin State | Local File Destination | Local File Destination | Console Destination | Console Destination | Syslog Remote Destination |
| --- | --- | --- | --- | --- | --- | --- | --- |
</caption>

<caption name="ACI-FABRIC-NAME - Syslog Remote Destination">

| Host Name/IP | Name | Admin State | Severity | Port | Forwarding Facility | Management EPG |
| --- | --- | --- | --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Syslog Collector must be defined in the input files:

<caption name="Syslog Collector Data Model">

```yaml
apic:
  fabric_policies:
    monitoring:
      syslogs:
        - name: syslog1
          description: desc1
          admin_state: false
          format: nxos
          show_millisecond: true
          show_timezone: true
          local_admin_state: false
          local_severity: emergencies
          console_admin_state: false
          console_severity: alerts
          destinations:
            - hostname_ip: 2.2.2.2
              name: dest1
              protocol: tcp
              port: 1234
              admin_state: false
              facility: local0
              severity: emergencies
              mgmt_epg: inb
            - hostname_ip: 2.2.2.3
```
</caption>

For further information on how the Syslog Collector is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/syslog/).



### TACACS Collector



TACACS is a security application providing a centralized validation of users attempting to gain access to network devices. The ACI Fabric can collect and send AAA data to an external TACACS collector by configuring TACACS monitoring destination groups. This data may include AAA session logs and AAA modifications such as new user addition or password change. See below tables for further configuration information.

<caption name="ACI-FABRIC-NAME - TACACS Monitoring Destination Group">

| Name | TACACS Destination |
| --- | --- |
</caption>

<caption name="ACI-FABRIC-NAME - TACACS Destination">

| Host Name/IP | Port | Authentication Protocol | Management EPG |
| --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the TACACS Collector must be defined in the input files:

<caption name="TACACS Collector Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      tacacs_providers:
        - hostname_ip: 1.1.1.1
          description: descr
          port: 4949
          protocol: chap
          key: '123'
          mgmt_epg: oob
          monitoring: true
          monitoring_username: user1
          monitoring_password: pass1
```
</caption>

For further information on how the TACACS Collector is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/tacacs/).



## ACI Snapshots



ACI provides a number of Import and Export Polices that are used to create backups (Export Policies) of Fabric configurations, use them to restore the Fabric (Import Policies) to a 'last-known good state' and also provide diagnostic information for Cisco TAC to aid in troubleshooting issues with the ACI Fabric.



### Remote Locations



One or more remote locations are created to receive ACI configuration backup.


<caption name="Remote Location Name Host Username">


| Remote Location Name | Host | Username | Remote Port | Remote Path | Protocol | EPG |
| --- | --- | --- | --- | --- | --- | --- |

</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Remote Locations must be defined in the input files:

<caption name="Remote Locations Data Model">

```yaml
apic:
  fabric_policies:
    remote_locations:
      - name: remote1
        description: desc1
        hostname_ip: 1.2.3.4
        protocol: scp
        path: /path
        port: 22
        auth_type: password
        username: cisco
        password: cisco
        mgmt_epg: inb
```
</caption>

For further information on how the Remote Locations are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/remote_location/).



### Export Configuration



Configuration should be backed up at least once a day. Backups can be triggered manually in the ACI GUI, or they can also run automatically with the usage of schedulers. Schedulers can be triggered to run only once or recurrently.

<caption name="Name Recurring Window One Time Window">

| Name | Recurring Window | One Time Window |
| --- | --- | --- |
| scheduler 1 | every-day | N/A |

</caption>

<caption name="Backup Configuration">

| Name | Format | Scheduler | Export Destination |
| --- | --- | --- | --- |
| export1 | json/xml | scheduler1 | remote1 |

</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Export configuration must be defined in the input files:

<caption name="Export Configuration Data Model">

```yaml
apic:
  fabric_policies:
    schedulers:
      - name: scheduler1
        description: desc1
    config_exports:
      - name: export1
        format: xml
        remote_location: remote1
        scheduler: scheduler1
```
</caption>

For further information on how Export configurations are defined in the IaC Data Model for ACI, please refer to the Network-as-Code (NaC) documentation for [Configuration Exports](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/config_export/) and [Schedulers](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/scheduler/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.003">
Automated configuration backups will be scheduled to run at least once per day using a recurring scheduler.
<br><br>
Rationale: Cisco recommends daily backups to minimise the risk of losing recent configuration changes in a disaster scenario. Automated scheduling removes the dependency on manual intervention and ensures consistent backup cadence.
</tip>
<br><br>





# Fabric Management



The ACI fabric can be managed out-of-band (OOB) and/or in-band. The out-of-band and in-band management interfaces can be used to allow administrative access to a node in the fabric, e.g., opening a remote terminal connection over SSH to a leaf node. The management interfaces are also used for out-of-band connections from nodes in the fabric, e.g., for remote authentication, sending syslog messages to a remote logging server, etc.

It is highly recommended to provide out-of-band management access to all nodes in the fabric, even if this will not be the primary interface used for monitoring and administrative access. The reason for this is to provide continued management access to the ACI fabric in the event that an issue with the fabric (maybe a bad configuration change) results in loss of in-band management connectivity. With out-of-band management, the network paths to access fabric management interfaces are not reliant on the fabric itself.

It is worth highlighting that it is possible to build an ACI fabric that will be managed in-band exclusively. However, if there is no out-of-band connectivity to the APICs, there will be some challenges during the set-up of the APICs and fabric discovery. It will be necessary to access the APIC GUI in order to register fabric nodes, and this will need to be done via the out-of-band management interface of an APIC. If there are no plans to have an out-of-band network as part of the long term operation of the fabric, then it will be necessary to arrange a temporary solution for access to the APIC out-of-band management interface in order to complete fabric discovery and set-up the in-band management interface of the APICs.
As described above, the choice to use only in-band management is not recommended by Cisco.



## APIC management



The APICs are a physical server appliance, where the hardware is a Cisco UCS C-series server, and the controller application software runs on top in a Linux OS (Operating System). The management of the APIC hardware is achieved through the CIMC (Cisco Integrated Management Controller) that is built-in to the Cisco UCS C-series server.

In a Cisco C-series server, the CIMC has a number of configurable options with regards to what physical interfaces can be used to reach the CIMC management IP interface. For an APIC, the only supported NIC mode is dedicated, which means that the CIMC management IP interface can only be reached via the separate physical port dedicated for CIMC access; dedicated also means that this physical port is not presented to any host operating system running on the server; it can only be used to access the CIMC, not the host OS.

Network connectivity to the APIC OS management IP is possible via the LOM (LAN on Motherboard) ports on the APIC, which are referred to in the APIC configuration guides as the out-of-band management ports. If configured, the APIC OS management IP can also be reached in-band through the 10GE/25GE ports on the Cisco VIC (Virtual Interface Card).

Given that all the APICs must use the dedicated NIC mode for CIMC access, it is necessary to connect this CIMC port on each of the APICs to the management network. This management network should be out-of-band of the ACI fabric.


<warning name="Warning">If the CIMC NIC mode is configured to anything other than dedicated, it may prevent the discovery of fabric nodes during fabric discovery.</warning>

In the %%customerName ACI design, all APIC dedicated CIMC ports will be connected to an out-of-band management network to enable management and monitoring of the APIC server hardware.



### APIC IP Addressing



For Fabric management setup, IP addresses need to be allocated for the following interfaces on APIC CIMC in the fabric.

The subnets from which IP addresses are allocated to different interfaces on the fabric are defined in the table below.

<caption name="fabric1 - APIC CIMC Fabric Management IP Addressing Summary">

| CIMC APIC Node Name | NodeID | OOB Management/mask | OOB Gateway |
| --- | --- | --- | --- |

</caption>

The IaC Data Model for ACI formally defines the format of the data input files. This is an example of how APIC management addresses must be defined in the input files:

<caption name="Management IP Addressing Data Model">

```yaml
apic:
  node_policies:
    nodes:
      - id: 1
        role: apic
        serial_number: [node-serial-number]
        name: APIC-1
        oob_address: 10.0.0.11/24
        oob_gateway: 10.0.0.1
        inb_address: 192.168.1.11/24
        inb_gateway: 192.168.1.1
      - id: 2
        role: apic
        serial_number: [node-serial-number]
        name: APIC-2
        oob_address: 10.0.0.12/24
        oob_gateway: 10.0.0.1
        inb_address: 192.168.1.12/24
        inb_gateway: 192.168.1.1
      - id: 3
        role: apic
        serial_number: [node-serial-number]
        name: APIC-3
        oob_address: 10.0.0.13/24
        oob_gateway: 10.0.0.1
        inb_address: 192.168.1.13/24
        inb_gateway: 192.168.1.1 |
```
</caption>

For further information on how APIC management addresses are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/node_policies/node_registration/).



### APIC Hardware Details







### Management Access Methods



The following table summarizes the different management access methods available for APIC hardware management:

<caption name="APIC Management Access Methods">

| Access Method | Interface | IP Address Source | Use Case |
| --- | --- | --- | --- |
| CIMC Management | Dedicated CIMC Port | Out-of-Band Network | Hardware management, BIOS, firmware updates |
| APIC OOB Management | LOM Ports (eth0) | Out-of-Band Network | APIC OS management, configuration |
| APIC InB Management | VIC Ports (bond0) | In-Band EPG | APIC OS management via fabric |

</caption>



### CIMC Access URLs



Direct HTTPS access to APIC CIMC interfaces:

<caption name="ACI-FABRIC-NAME - CIMC Access URLs">

| Node Name | CIMC IP Address | CIMC HTTPS URL | Purpose |
| --- | --- | --- | --- |

</caption>

<note name="Note">Ensure proper firewall rules and access controls are in place for CIMC management interfaces.</note>



### Management Network Connectivity




<tip>Always configure out-of-band management for reliable access to APIC controllers, especially during fabric maintenance or troubleshooting scenarios.</tip>



## ACI Out-of-Band



Each node in the fabric has at least one physical interface that provides out-of-band management access to the operating system. For leaf and spine nodes, these are the mgmt0 ports. On the APICs, these are the eth1-1 and eth1-2 ports that correspond to the LOM (LAN on Motherboard) ports.

The APICs also have a dedicated "lights-out" management port that provides out-of-band management access to the underlying server's CIMC (Cisco Integrated Management Controller) that allows management and monitoring of the server hardware platform.

If out-of-band management is used, the network path to/from the out-of-band network does not transit the ACI fabric. The following approach is used, i.e., keeping the ACI fabric out of the data path for connections to the out-of-band management interfaces of fabric nodes. This is to avoid any dependency on the ACI fabric for access to the out-of-band management interface of a node in the ACI fabric.

Technically, it would be possible to create a design where the network path to/from the OOB network is via the ACI fabric (ACI as a transit network to reach the OOB network). A decision to ignore Cisco's general recommendation would carry the risk that errors on the ACI fabric could cut-off out-of-band management access.

The following nodes will have their out-of-band management interfaces connected to the out-of-band management network:

- All APIC eth1-1 or eth1-2 interfaces (OOB Mgmt). %%customerName will only connect one of the two.
- All spine mgmt0 interfaces (on both supervisors).
- All leaf mgmt0 interfaces.
- All UCS server's CIMC interfaces, those of the APIC servers.

For further information regarding the physical out-of-band connectivity, refer to the OOB Connectivity Section in the ACI Physical design chapter.

The following design decisions have been made in this section:

<tip name="Design Decision DD.004">
Out-of-band management connectivity will be provided to all nodes in the fabric, and the OOB network path will not transit the ACI fabric.
<br><br>
Rationale: Cisco highly recommends that the OOB management network path does not traverse the ACI fabric itself. This avoids a circular dependency where a fabric issue could simultaneously cut off management access to the very devices that need troubleshooting. Dedicated OOB connectivity ensures continued administrative access during fabric outages or misconfigurations.
</tip>
<br><br>




### OOB Management Access Policy



Each OOB interface on the nodes in the fabric represents an endpoint. The ACI policy model puts endpoints into an EPG (EndPoint Group), and the OOB management interfaces are no exception; they are associated with a special EPG called an out-of-band management EPG. This association is formed by allocating nodes to an OOB management EPG. Each node in the EPG is assigned an IP address, either by static assignment, or automatically from a pool associated with the EPG. The allocated IP address is then configured on the OOB management port of the corresponding node.

The following figure shows an overview of the Mgmt Tenant out-of-band fabric management access policy:


<caption name="ACI Out-of-band Management Access Policy">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/ACI_Out-of-band_Management_Access_Policy.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


The management profile includes the out-of-band EPG MO (Managed Object) that provides access to management functions via the out-of-band contract (vzOOBBrCP). The out-of-band contract enables the external management instance profile (mgmtExtInstP) EPG to consume the out-of-band EPG. This exposes the fabric node OOB management interfaces to locally or remotely connected devices, according to the policy configured in the contract. For example, if the OOB contract permits TCP port 22, this will allow SSH access to the OOB management interfaces from a remote SSH client.

The External Management Network Instance Profile specifies one or more subnets. These subnets effectively identify the external endpoints (by their IP address) that belong to the external management instance profile, which can be considered as an external EPG. Endpoints within the IP ranges specified by the subnets are permitted to communicate to/from the OOB management EPG using the protocols and ports permitted by the out-of-band contract. If an external device is not within the range of the subnets configured in the external management instance profile, they will not have out-of-band access.

To provide and consume contracts for OOB devices using default/common contract (Permit Any/Any) you should run two steps:

Step 1- Providing contract.

Provide the appropriate contract. This could be default/common contract or a specific contract you have created.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Provided Out-of-Band Contracts must be defined in the input files:

<caption name="Out-of-band Endpoint Group Data Model">

```yaml
apic:
  tenants:
    - name: mgmt
      oob_contracts:
        - name: OOB-CON1
          alias: OOB-SUB-ALIAS
          description: My Desc
          scope: context
          subjects:
            - name: OOB-SUB
              filters:
                - filter: ALL
```
</caption>

For further information on how the Provided Out-of-Band Contracts are defined in the IaC Data Model for ACI, please refer to the Network-as-Code (NaC) documentation for [OOB Endpoint Groups](https://netascode.cisco.com/docs/data_models/apic/tenants/oob_endpoint_group/) and [OOB Contracts](https://netascode.cisco.com/docs/data_models/apic/tenants/oob_contract/).

Step 2- Consuming the contract.

- Consume the same contract that has been provided in step 1.
- Enter the subnet(s) that are allowed to have access to the OOB network (0.0.0.0/0 permits any).

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Consumed Out-of-Band Contracts must be defined in the input files:

<caption name="External Management Instance Data Model">

```yaml
apic:
  tenants:
    - name: mgmt
      ext_mgmt_instances:
        - name: EXT1
          subnets:
            - 0.0.0.0/0
          oob_contracts:
            consumers:
              - OOB-CON1
```
</caption>

For further information on how the Consumed Out-of-Band Contracts are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/oob_ext_mgmt_instance/).



## ACI In-Band



It is possible to configure each node in the fabric with an in-band management interface, which provides management access to the device. This is a logical interface on each node that sits in the built-in Mgmt Tenant and can be accessed via in-band network connections, i.e., via the main leaf node fabric ports.

The following design decisions have been made in this section:

<tip name="Design Decision DD.005">
In-band management access will be configured as a backup to out-of-band management, with appropriate access policies and security controls in place.
<br><br>
Rationale: This section can be included for reference in case in-band management is required.
</tip>
<br><br>




### INB Management Access Policy



Each INB interface on the nodes in the fabric represents an endpoint. The ACI policy model puts endpoints into an EPG (EndPoint Group), and the INB management interfaces are no exception; they are associated with a special EPG called an in-band management EPG. This association is formed by allocating nodes to an INB management EPG. Each node in the EPG is assigned an IP address, either by static assignment, or automatically from a pool associated with the EPG. The allocated IP address is then configured on the INB management interface (which will be a VLAN interface) of the corresponding node.

The following figure shows an overview of the Mgmt Tenant in-band fabric management access policy:


<caption name="ACI In-band Management Access Policy">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/ACI_In-band_Management_Access_Policy.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


The management profile includes the in-band EPG MO (Managed Object) that provides access to management functions via a contract (vzBrCP). The contract used for in-band management EPGs is just a standard contract; they are not special contracts like those used for out-of-band management. The contract used for in-band management enables other EPGs to consume the in-band EPG. This exposes the fabric node INB management interfaces to locally or remotely connected devices, according to the policy configured in the contract. For example, if the INB contract permits TCP port 161, this will allow SNMP polling to the INB management interfaces from a management station, connected via an application EPG, L2 Out or L3 Out.

If using EPG extension (of the "Application EPG"), it is possible to put the Application EPG into the same bridge domain as the "In-band EPG". This would typically be used where the in-band management IP interfaces of ACI components (which sit in the In-band EPG) will use a default gateway that is external to the fabric. In this model it is not necessary to configure a subnet on the BD associated with the In-band EPG. Alternatively, the Application EPG can be in a separate bridge domain, which would require traffic to be routed externally between the subnet associated with Application EPG and that of the In-band EPG, which is the subnet for the BD configured for the In-band EPG.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how to define an In-band Endpoint Group :

<caption name="In-band Endpoint Group Data Model">

```yaml
apic:
  tenants:
    - name: mgmt
      inb_endpoint_groups:
        - name: INB
          vlan: 2
          bridge_domain: inb
          contracts:
            consumers:
              - STD-CON1
            providers:
              - STD-CON1
```
</caption>

For further information on how the In-band Endpoint Groups are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/inb_endpoint_group/).



## ACI IP Addressing



For Fabric Management setup, IP addresses need to be allocated for the following interfaces on different nodes in the fabric:

- Leaf node OOB and/or INB management.
- Spine node OOB and/or INB management.
- APIC OOB and/or INB management.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the OOB and INB IP addresses need to be defined in the input file.

<caption name="Management IP Addressing Data Model">

```yaml
apic:
  node_policies:
    nodes:
      - id: 101
        oob_address: 10.1.1.1/24
        oob_gateway: 10.1.1.254
        inb_address: 10.10.10.1/24
        inb_gateway: 10.10.10.254
      - id: 1001
        oob_address: 10.1.1.10/24
        oob_gateway: 10.1.1.254
        inb_address: 10.10.10.10/24
        inb_gateway: 10.10.10.254
```
</caption>

This is an example of parameters for INB management (BD, VRF, L3Out etc) and OOB management contract:

<caption name="INB Management Data Model">

```yaml
apic:
  access_policies:
    leaf_switch_profiles:
      - name: LEAF1001_INB
        selectors:
          - name: SEL1_INB
            node_blocks:
              - name: BLOCK_INB
                from: 1001
        interface_profiles:
          - LEAF1001_INB
    leaf_interface_profiles:
      - name: LEAF1001_INB
        selectors:
          - name: SEL1_INB
            policy_group: PG_INB
            port_blocks:
              - name: BLOCK_INB
                description: Inband MGMT
                from_port: 1
    leaf_interface_policy_groups:
      - name: PG_INB
        description: Inbound Policy Group
        type: access
        link_level_policy: 10G
        cdp_policy: CDP-ENABLED
        lldp_policy: LLDP-ENABLED
        spanning_tree_policy: BPDU-FILTER
        mcp_policy: MCP-ENABLED
        l2_policy: PORT-LOCAL
        storm_control_policy: 10P
        port_channel_policy: LACP-ACTIVE
        port_channel_member_policy: FAST
        aaep: AAEP_INB
    aaeps:
      - name: AAEP_INB
        infra_vlan: true
        physical_domains:
          - PHY_INB
    physical_domains:
      - name: PHY_INB
        vlan_pool: VLAN_POOL_INB
    vlan_pools:
      - name: VLAN_POOL_INB
        description: "Inband MGMT VLAN Pool"
        allocation: static
        ranges:
          - from: 4000
            role: external
            description: "Inband VLAN Pool Range"
  tenants:
    - name: 'mgmt'
      bridge_domains:
        - name: 'inb'
          unknown_unicast: proxy
          vrf: inb
          subnets:
            - ip: 10.x.x.x/24
              public: true
              private: false
      inb_endpoint_groups:
        - name: 'EPG_INB'
          vlan: 3913
          bridge_domain: inb
          contracts:
            consumers:
              - CON_L3O
            providers:
              - CON_MGMT
      l3outs:
        - name: 'L3O_MGMT'
          vrf: inb
          domain: DOM_L3O_CORE
          node_profiles:
            - name: 'LNP_1103'
              nodes:
                - node_id: 1103
                  router_id: 22.1.194.2
              interface_profiles:
                - name: 'LIP_1103'
                  interfaces:
                    - node_id: 1103
                      port: 48
                      ip: 22.1.193.0/31
                      vlan: 1500
                      bgp_peers:
                        - ip: 22.1.193.1
                          remote_as: 64900
                    - node_id: 1103
                      port: 47
                      ip: 22.1.193.2/31
                      vlan: 1500
                      bgp_peers:
                        - ip: 22.1.193.3
                          remote_as: 64900
          external_endpoint_groups:
            - name: 'EXTEPG_MGMT'
              subnets:
                - prefix: 0.0.0.0/0
              contracts:
                providers:
                  - CON_L3O
          export_route_map:
            type: global
            contexts:
              - name: RCONTROL
                match_rule: MATCH_MGMT
      contracts:
        - name: 'CON_L3O'
          subjects:
            - name: 'SBJ_L3O'
              filters:
                - filter: FLT_PERMIT_ANY
        - name: 'CON_MGMT'
          subjects:
            - name: 'SBJ_MGMT'
              filters:
                - filter: FLT_PERMIT_ANY
      oob_contracts:
        - name: 'CON_OOB'
          subjects:
            - name: 'SUB_OOB'
              filters:
                - filter: FLT_PERMIT_ANY
  policies:
    match_rules:
      - name: 'MATCH_MGMT'
        prefixes:
          - ip: 22.1.200.0/24
          - ip: 22.1.201.0/24
```
</caption>

For further information on how the OOB and INB IP addresses are defined in the IaC Data Model for ACI, please refer to the Network-as-Code (NaC) documentation for [OOB Node Addresses](https://netascode.cisco.com/docs/data_models/apic/node_policies/oob_node_address/) and [INB Node Addresses](https://netascode.cisco.com/docs/data_models/apic/node_policies/inb_node_address/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.006">
For this design, OOB management IP addresses for all nodes will be configured using static assignment
<br><br>
Rationale: IP addresses will be assigned statically to control which address is assigned to which device based on the IP addressing convention
</tip>
<br><br>

<tip name="Design Decision DD.007">
For this design, INB management IP addresses for all nodes will be automatically allocated from an address pool.
<br><br>
Rationale: IP addresses will be automatically allocated from an address pool which simplifies configuration in a large scale fabrics
</tip>
<br><br>





# Fabric Polices



Fabric policies govern the operation of internal fabric interfaces and enable the configuration of various functions, protocols, and interfaces that connect spine and leaf switches. The following figure provides an overview of the fabric policy model.


<caption name="Fabric Policies">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Fabric_Polices.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


Fabric policies enable features such as monitoring (statistics collection and statistics export), troubleshooting (on-demand diagnostics and SPAN), IS-IS, council of oracle protocol (COOP), SNMP, Border Gateway Protocol (BGP) route reflectors, DNS, or Network Time Protocol (NTP).
The following figures provide an overview of the relationship between different Fabric Policies objects.


<caption name="POD Policies Object Relationship">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/POD_Policies_Object_Relationship.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>



<caption name="Fabric Policies Object Relationship">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Fabric_Policies_Object_Relationship.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




## Pods



The ACI Fabric POD policy group is used to combine the different policies that dictate the behavior of the fabric Pod (NTP, SNMP, etc.) into a group. This group is applied to the Pod profile.

This can be configured under: Fabric > Fabric Policies > Pods > Policy Groups

<caption name="ACI-FABRIC-NAME - POD Policy Group">

| POD Policy Group Name | Description | SNMP | Time | Management |
| --- | --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Pod Policy Group must be defined in the input files:

<caption name="POD Policy Groups Data Model">

```yaml
apic:
  fabric_policies:
    pod_policy_groups:
      - name: POD1
        snmp_policy: SNMP1
        date_time_policy: NTP1
```
</caption>

For further info on how the Pod Policy Group are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/pod_policy_group/).

**ISIS Metric**

The default ISIS redistribution metric is 63, which is the maximum configurable metric. When an inter-pod router (IPN) spine is removed from the fabric and then reintroduced a hold down timer is applied to prevent forwarding on the spine until ISIS has fully converged. During this time, the metric is set to the maximum available (63) to prevent forwarding. Unfortunately, this is the same value as the default metric, so traffic begins forwarding immediately, and traffic loss may occur. CSCvd75131 was filed to address this issue.

CSCvd75131 is first addressed in 2.2(4f); however, even with CSCvd75131 in place, the fix for this issue still requires a manual configuration change. The fix in CSCvd75131 is to enable the ability to change the metric; however, the metric must be manually updated to a value that addresses the original issue . The ISIS metric should be set to 32, or any value below 63. This is configured even for single-pod environments. Configuring this for a single pod has no impact and future-proofs the configuration in the event that the environment moves to multi-pod.

The metric can be configured at Fabric > Fabric Policies > Policies > Pod > ISIS Policy default > ISIS metric for redistributed routes

<caption name="ISIS Metric Data Model">

```yaml
apic:
  fabric_policies:
    fabric_isis_redistribute_metric: 32
```
</caption>

The following design decisions have been made in this section:

<tip name="Design Decision DD.008">
The ISIS redistribution metric will be set to 32 instead of the default value of 63.
<br><br>
Rationale: Cisco recommends setting the ISIS metric to a value below the maximum (63) to prevent traffic loss when an IPN spine is removed and reintroduced into the fabric. The default metric of 63 coincides with the hold-down metric, causing premature forwarding before ISIS has fully converged. Setting the metric to 32 future-proofs the configuration for multi-pod even in single-pod deployments.
</tip>
<br><br>




### POD Profile



The POD Policy Group is applied on the default POD Profiles to enforce the configured policies. This can be configured under: Fabric > Fabric Policies > Pods > Profiles

Pod Profiles will use a following naming convention: POD_[ID]

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Pod Profile must be defined in the input files:

<caption name="POD Profile Data Model">

```yaml
apic:
  auto_generate_switch_pod_profiles: true
  fabric_policies:
    pod_profile_name: "POD\\g<id>"
    pod_profile_pod_selector_name: "POD\\g<id>"
```
</caption>

For further info on how the Pod Profile are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/pod_profile/).



## Switches



Switch policies are grouped into switch policy groups. A switch policy group is then applied to a switch profile. Leaf and Spine profiles need to be defined separately. Switch profiles and switch policy groups exist in both Fabric Policies and Access Policies to separate internal facing interfaces and policies from the external facing interfaces.



### Fabric Switch Policy Groups



Switch Policy Groups are templates for grouping the defined switch profiles. This can be configured under: Fabric > Fabric Policies > Switches > [Leaf/Spine] Switches > Policy Groups

A policy group can be associated to the Leaf and Spine profile defined in the next paragraph.

Two Switch policy groups will be created, one for the Spine switches and one for the Leaf switches.

<caption name="ACI-FABRIC-NAME - Fabric Policy Switch Policy Groups">

| Name | Type | Monitoring Policy | TechSupport Policy | Core Policy | Inventory Policy | PSU Policy | Node Control Policy |
| --- | --- | --- | --- | --- | --- | --- | --- |
</caption>

These Switch policy groups are used as policy containers for the following policy types:

- Monitoring Policy: mon_pol
- TechSupport Export Policy: tech_pol
- Core Export Policy: core_pol
- Call Home Inventory Policy: inv_pol
- Power redundancy Policy: pwr_pol
- Fabric Node control Policy: node_pol
- Analytics policy: default
- TWAMP server policy:default
- TWAMP responder policy:default

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Fabric Leaf Switch Policy Group must be defined in the input files:

<caption name="Leaf Switch Policy Group Data Model">

```yaml
apic:
  fabric_policies:
    leaf_switch_policy_groups:
      - name: ALL_LEAFS
        psu_policy: COMBINED
        node_control_policy: DOM_NETFLOW
```
</caption>

For further info on how the Fabric Leaf Switch Policy Group are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fp_leaf_switch_policy_group/).

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Fabric Spine Switch Policy Group must be defined in the input files:

<caption name="Switch Policy Group Data Model">

```yaml
apic:
  fabric_policies:
    spine_switch_policy_groups:
      - name: ALL_SPINES
        psu_policy: COMBINED
        node_control_policy: DOM_NETFLOW
```
</caption>

For further info on how the Fabric Spine Switch Policy Group are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fp_spine_switch_policy_group/).



### Fabric Switch Profiles



Switch Profiles are used to associate Switch Policy Groups to Fabric Switches. This can be configured under: Fabric > Fabric Policies > Switches > [Leaf/Spine] Switches > Profiles

<caption name="ACI-FABRIC-NAME - Spine Switch Profile">

| Profile Name | Selectors | Policy | Node IDs | Interface Profiles |
| --- | --- | --- | --- | --- |
</caption>

<caption name="ACI-FABRIC-NAME - Leaf Switch Profile">

| Profile Name | Selectors | Policy | Node IDs | Interface Profiles |
| --- | --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Fabric Leaf Switch Profile must be defined in the input files:

<caption name="Leaf Switch Profile Data Model">

```yaml
apic:
  fabric_policies:
    leaf_switch_profiles:
      - name: LEAF1001
        selectors:
          - name: SEL1
            policy: ALL_LEAFS
            node_blocks:
              - name: BLOCK1
                from: 1001
        interface_profiles:
          - LEAF1001
```
</caption>

For further info on how the Fabric Leaf Switch Profile are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fp_leaf_switch_profile/).

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Fabric Spine Switch Profile must be defined in the input files:

<caption name="Spine Switch Profile Data Model">

```yaml
apic:
  fabric_policies:
    spine_switch_profiles:
      - name: SPINE101
        selectors:
          - name: SEL1
            policy: ALL_SPINE
            node_blocks:
              - name: BLOCK1
                from: 101
        interface_profiles:
          - SPINE101
```
</caption>

For further info on how the Fabric Spine Switch Profile are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fp_spine_switch_profile/).



### Fabric Switch Overrides



An Override policy allows a selected range of nodes within the specified policy group to apply an alternate policy or policies instead of the currently configured policies applied to that policy group.

This can be configured under: Fabric > Fabric Policies > Switches > [Leaf/Spine] Switches > Overrides



## Modules



Module policy groups only contain the monitoring policy to be applied to the module profile. Leaf and Spine profiles need to be defined separately.

**Module Policy Groups and Profiles**

A leaf or spine module port policy group enables you to apply the defined monitoring policy. This can be configured under:

- Fabric > Fabric Policies > Modules > [Leaf/Spine] Modules > Profiles
- Fabric > Fabric Policies > Modules > [Leaf/Spine] Modules > Policy Groups

The module policy group needs to be applied to the profile



## Interfaces



The ACI Fabric Policies chapter introduces the foundational policies that govern the behavior and configuration of the ACI fabric, including how the fabric elements such as spines and leaves are discovered, added, and managed automatically. It highlights the automation of underlay and overlay protocols like IS-IS and VXLAN, enabling simplified fabric expansion and centralized management through the APIC, which reduces manual configuration and operational complexity.

- Interface policies are grouped into Interface policy groups.
- An interface policy group is then applied to an interface profile.
- Leaf and Spine profiles need to be defined separately.



### Fabric Interface Policy Groups



A leaf or spine port policy group enables you to apply policies to a group of leaf or spine ports. This can be configured under: Fabric > Fabric Policies > Interfaces > [Leaf/Spine] Interfaces > Policy Groups

Following table summarize Fabric Leaf Interface policy groups created.

<caption name="ACI-FABRIC-NAME - Fabric Interface Policy Groups">


| Name | Description | Link Level Policy |
| --- | --- | --- |

</caption>

<caption name="Fabric Leaf Interface Policy">

```yaml
apic:
  fabric_policies:
    leaf_interface_policy_groups:
      - name: ALL_LEAF
        description: All Leaf Interfaces
        link_level_policy: link-level-policy1
```
</caption>

For further info on how the SNMP Pod Policy are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fp_leaf_interface_policy_group/).



### Fabric Interface Profiles



The leaf and spine fabric port profiles contain leaf and spine port selectors that can associate with their respective policy groups.

This can be configured under: Fabric > Fabric Policies > Interfaces > [Leaf/Spine] Interfaces > Profiles

<caption name="ACI-FABRIC-NAME - Fabric Spine Interface Profile">

| Name | Description |
| --- | --- |
</caption>

<caption name="ACI-FABRIC-NAME - Fabric Leaf Interface Profile">

| Name | Description |
| --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Fabric Leaf Interface Profile must be defined in the input files:

<caption name="Fabric Leaf Interface Profile Data Model">

```yaml
apic:
  fabric_policies:
    leaf_interface_profiles:
      - name: LEAF1001
```
</caption>

For further info on how the Fabric Leaf Interface Profile are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fp_leaf_interface_profile/).

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Fabric Spine Interface Profile must be defined in the input files:

<caption name="Fabric Spine Interface Profile Data Model">

```yaml
apic:
  fabric_policies:
    spine_interface_profiles:
      - name: SPINE101
```
</caption>

For further info on how the Fabric Spine Interface Profile are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fp_spine_interface_profile/).



### Fabric Interface Overrides



An Override policy allows a selected range of interfaces within the specified policy group to apply an alternate policy or policies instead of the currently configured policies applied to that policy group. This can be configured under: Fabric > Fabric Policies > Interfaces > [Leaf/Spine] Interfaces > Overrides



## Polices







### Fabric Switch Policies







### Power Supply Redundant Policies




The Nexus 9000 series switches can operate in three modes with regards to power supply redundancy:

- Combined (default configuration), this mode allocates the combined power of all power supplies to active power for switch operations. This mode does not allocate reserve power for power redundancy in case of power outages or power supply failures.
- N+1 (ps-redundancy), this mode allocates one power supply as a reserve power supply in case an available power supply fails. The remaining power supplies are allocated for available power. The reserve power supply must be at least as powerful as each power supply used for the available power.
- N+N, also known as Grid-redundancy which leverages two separate power feeds. This mode ensures load sharing, but the budget becomes half the total PSU capacity. Use a different power source for the active and reserve power sources, so that if the power source that is used for active power fails, the reserve power supply can provide power for the switch.
- The power redundancy mode is dictated by the application of a power supply policy.

Configured under: Fabric > Fabric Policies > Policies > Switch > Power Supply Redundancy > default

The following power supply policies are created:

<caption name="ACI-FABRIC-NAME - Power Supply Policies">

| Policy Name | Power Supply Mode |
| --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Power Supply Redundancy must be defined in the input files.

<caption name="Power Supply Redundancy Policy Data Model">

```yaml
apic:
  fabric_policies:
    switch_policies:
      psu_policies:
        - name: COMBINED
          admin_state: combined
```
</caption>

For further info on how the Power Supply Redundancy are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/psu_policy/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.009">
Nexus 9300 switches with two power supplies will use the N+1 redundancy policy, and Nexus 9500 switches with multiple power supplies will use N+1 or N+N based on customer requirements.
<br><br>
Rationale: Cisco recommends N+1 redundancy for dual-PSU switches to ensure continued operation if one power supply fails. For chassis-based switches with more power supplies, N+N (grid redundancy) may be used to protect against the loss of an entire power feed, providing an additional layer of resilience.
</tip>
<br><br>




### Fabric Global Policies







### DNS Profiles




Configuring DNS in an ACI fabric consists of two tasks:

- Create a DNS Profile (default), which contains the information about DNS providers and DNS domains.
- Associate this DNS Profile as a DNS label under the required Tenant.

This is configured under: Fabric > Fabric Policies > Policies > Global > DNS Profiles > default

The DNS Profile creation is a fabric global policy. The below table shows the properties to be added when creating a DNS profile.

<caption name="ACI-FABRIC-NAME - DNS Profile">

</caption>

In order to apply the DNS configuration to the switch nodes and the APIC controllers, the DNS Profile is applied to the mgmt Tenant as a DNS label.

This is configured under: Tenants > mgmt > Networking > VRFs > oob > Policy > DNS labels

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the DNS Profile Policy must be defined in the input files:

<caption name="DNS Profile Policy Data Model">

```yaml
apic:
  fabric_policies:
    dns_policies:
      - name: DNS-1
        mgmt_epg: oob
        providers:
          - ip: 1.1.1.1
            preferred: true
          - ip: 1.1.1.2
            preferred: false
        domains:
          - name: cisco.com
            default: true
```
</caption>

For further info on how the DNS Profile Policy are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/dns_policy/).



### Fabric L2 MTU Policy




This policy is used for configuring fabric-wide layer 2 MTU. The L2 MTU is set at 9000 bytes, which is the default value. This is configured under: Fabric > Fabric Policies > Policies > Global > Fabric L2 MTU > default

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Fabric L2 MTU must be defined in the input files:

<caption name="Fabric L2 MTU Policy Data Model">

```yaml
apic:
  fabric_policies:
    l2_port_mtu: 9216
```
</caption>

For further info on how the Fabric L2 MTU are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/l2_mtu/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.010">
The Fabric L2 MTU policy will remain at the default value of 9000 bytes.
<br><br>
Rationale: Common practice is to leave the fabric-wide L2 MTU at its default. The default of 9000 bytes accommodates jumbo frames, and modifying this value is only necessary in specific scenarios that do not apply to this deployment.
</tip>
<br><br>




### LLDP Policy




LLDP allows network devices to advertise information about themselves to other devices in the network. This protocol runs over the data-link layer, which allows two systems running different network layer protocols to learn about each other.

This is configured under: Fabric > Fabric Policies > Policies > Global > LLDP Policy default

LLDP policy is used to set fabric wide LLDP settings; it does dictate LLDP port configuration.

Table below shows default parameters.

<caption name="LLDP Policy defaults">

| Parameters | Values |
| --- | --- |
| Transmit State | Enabled |
| Receive State | Enabled |
</caption>

The following design decisions have been made in this section:

<tip name="Design Decision DD.011">
The fabric-wide LLDP policy will remain at default settings with both transmit and receive states enabled.
<br><br>
Rationale: Common practice is to leave the fabric-wide LLDP policy at its default. LLDP provides valuable neighbor discovery and topology visibility, and the default enabled state supports standard fabric operations without introducing additional complexity.
</tip>
<br><br>




### Fabric POD Policies







### Date and Time




In this design, APIC controllers and switch nodes (leaf and spine) will be synchronized by external NTP servers. NTP synchronizes time amongst a set of distributed servers and clients. This synchronization allows events to be correlated when system logs are created and other time-specific events occur.

Date and Time Format is configured under: System > System Settings > Date and Time

<caption name="ACI-FABRIC-NAME - Date and Time Format Properties">

| Date and Time Format Property | Value |
| --- | --- |
| Display Format | N/A |
| Timezone | N/A |
| Show Offset | Yes |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Date and Time Format must be defined in the input files:

<caption name="Date and Time Policy Data Model">

```yaml
apic:
  fabric_policies:
    date_time_format:
      display_format: local
      timezone: p0_UTC
      show_offset: true
```
</caption>

For further info on how the Date and Time Format are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/date_time_format/).

The NTP Policy has the following parameters:

<caption name="ACI-FABRIC-NAME - Date and Time Policy">

</caption>

This can be configured under: Fabric > Fabric Policies > Policies > POD > Date and Time > Policy default

<caption name="ACI-FABRIC-NAME - NTP Servers">

| Hostname/IP | Preferred | Management EPG |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Date and Time Policy must be defined in the input files:

<caption name="Date and Time Policy Data Model">

```yaml
apic:
  fabric_policies:
    pod_policies:
      date_time_policies:
        - name: NTP1
          ntp_admin_state: true
          ntp_auth_state: false
          apic_ntp_server_state: false
          apic_ntp_server_master_mode: false
          apic_ntp_server_master_stratum: 8
          ntp_servers:
            - hostname_ip: 1.1.1.13
              auth_key_id: 1
              preferred: true
              mgmt_epg: oob
              ntp_keys:
                - id: 1
                  key: key1
                  auth_type: md5
                  trusted: false
```
</caption>

For further info on how the Date and Time Format are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/date_time_policy/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.012">
At least two external NTP servers will be configured for fabric time synchronisation.
<br><br>
Rationale: Cisco recommends configuring redundant NTP servers to ensure reliable time synchronisation across all fabric nodes. Accurate and consistent timestamps are essential for correlating syslog events, troubleshooting, and maintaining correct certificate validation across the fabric.
</tip>
<br><br>




### SNMP Policy




The SNMP policy enables you to monitor client group, v3 user, and/or community SNMP policies. This can be configured under: Fabric > Fabric Policies > Policies > Pod > SNMP > default

ACI supports SNMP Read Only.

<caption name="ACI-FABRIC-NAME - SNMP Policy">

| SNMP Policy | Value |
| --- | --- |
</caption>

The SNMP community profile parameters are as follows:

<caption name="ACI-FABRIC-NAME - SNMP Communities">

| Community |
| --- |
</caption>

The name of the community policy can be between 1 and 64 alphanumeric characters. It cannot contain the @ symbol.

The SNMP user profile is used to associate users with SNMP policies for monitoring devices in a network.

<caption name="ACI-FABRIC-NAME - SNMP User Profiles">

| User Name | Privacy Type | Authorization Type |
| --- | --- | --- |
</caption>

The authorization type is a message authorization code that is used between two parties sharing a secret key to validate information transmitted between them. HMAC (Hash MAC) is based on cryptographic hash functions. It can be used in combination with any iterated cryptographic hash function. HMAC SHA1 and HMAC SHA2 are two constructs of the HMAC using the SHA1 hash function and the SHA2 hash function. HMAC also uses a secret key for calculation and verification of the message authentication values.

Supported types are:

- HMAC-SHA1-96 - The authentication type with SHA1 hash function (96-bit hash value)
- HMAC-SHA2-224 - The authentication type with SHA2 hash function (224-bit hash value)
- HMAC-SHA2-256 - The authentication type with SHA2 hash function (256-bit hash value)
- HMAC-SHA2-384 - The authentication type with SHA2 hash function (384-bit hash value)
- HMAC-SHA2-512 - The authentication type with SHA2 hash function (512-bit hash value)

The default is HMAC-SHA1-96.

The privacy (encryption) type for the user profile. The type can be Advanced Encryption Standard (AES). Data Encryption Standard is a method of data encryption that uses a private (secret) key. Advanced Encryption Standard that uses a key with a length of 128 bits to encrypt data blocks with a length of 128 bits. The privacy types are:

- None - No encryption
- AES-128 - Advanced Encryption Standard that uses a key with a length of 128 bits to encrypt data blocks with a length of 128 bits.

The default is None.

A client group is a group of client IP addresses that allows SNMP access to routers or switches.

<caption name="ACI-FABRIC-NAME - SNMP Client Groups">

| Client Group Name | Management EPG | Client IP |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the SNMP Pod Policy must be defined in the input files:

<caption name="SNMP Policy Data Model">

```yaml
apic:
  fabric_policies:
    pod_policies:
      snmp_policies:
        - name: SNMP1
          admin_state: true
          location: LOCATION
          contact: CONTACT
          users:
            - name: USER1
              privacy_type: aes-128
              privacy_key: Key123456
              authorization_type: hmac-sha1-96
              authorization_key: Key123456
          communities:
            - abcABC123
          clients:
            - name: CLIENTS
              mgmt_epg: inb
              entries:
                - name: NMS1
                  ip: 1.1.1.1
```
</caption>

For further info on how the SNMP Pod Policy are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/snmp_policy/).



### Management Access




The Management access policy enforces rules applied on the access to the system (Telnet, SSH, HTTP/HTTPS, etc.). This is configured under: Fabric > Fabric Policies > Policies > Pod > Management Access > default

Default policies for each protocol are shown in the tables below.

<caption name="ACI-FABRIC-NAME - Telnet">

| Protocol | Admin Status | Port |
| --- | --- | --- |
</caption>

<caption name="ACI-FABRIC-NAME - SSH">

| Protocol | Admin Status | Port |
| --- | --- | --- |
</caption>

<caption name="ACI-FABRIC-NAME - HTTP">

| Protocol | Admin Status | Port |
| --- | --- | --- |
</caption>

<caption name="ACI-FABRIC-NAME - HTTPS">

| Protocol | Admin Status | Port |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Management Access Policy must be defined in the input files:

<caption name="Management Access Policy Data Model">

```yaml
apic:
  fabric_policies:
    pod_policies:
      management_access_policies:
        - name: MGMT1
          telnet:
            admin_state: true
          ssh:
            port: 22
            hmac_sha1: false
            chacha: false
          https:
            tlsv1: true
          http:
            admin_state: true
            port: 8080
```
</caption>

For further info on how the Management Access Policy are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/management_access_policy/).



### Fabric Monitoring Policies




A named monitoring policy can be defined, or the default policy can be used.

Policies for Stats collection, Call home, SNMP, Syslog, etc, are defined under Monitoring Policies. Administrators can create monitoring policies with the following four broad scopes:

- Fabric Wide: includes both fabric and access objects.
- Fabric: fabric ports, cards, chassis, fans, and so on.
- Access (also known as infrastructure): access ports, FEX, VM controllers, and so on.
- Tenant: EPGs, application profiles, services, and so on.



### Fabric Node Controls Policy




The following Fabric Node Controls policy allows controlling some Switch level features:

- Activation of Digital Optical Monitoring (DOM)
- Priority of Telemetry vs Netflow vs Analytics

This is configured under:

Fabric > Fabric Policies > Policies > Monitoring > Fabric Node Controls

ACI switch hardware supports only one feature at the same time, either NetFlow or Telemetry or Analytics. If the APIC pushes Cisco Analytics and NetFlow and Telemetry configurations to a particular node, the chosen priority flag alerts the switch as to which feature is given priority. The other feature configuration is ignored.

For APIC applications like NDI (Nexus Dashboard Insight), the Telemetry Priority is required. For Cisco Tetration, the Analytics Priority option is required. The default is Telemetry Priority.

DOM is not supported on all type of Optics as described in the [Cisco DOM Compatibility Matrix](https://www.cisco.com/c/en/us/td/docs/interfaces_modules/transceiver_modules/compatibility/matrix/DOM_matrix.html).

In this design, the following Fabric Node Control policy will be used:

<caption name="ACI-FABRIC-NAME - Fabric Node Controls">

| Policy Name | DOM | Telemetry Priority |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Node Control Switch Policy must be defined in the input files:

<caption name="Fabric Node Control Policy Data Model">

```yaml
apic:
  fabric_policies:
    switch_policies:
      node_control_policies:
        - name: DOM_NETFLOW
          dom: true
```
</caption>

For further info on how the Node Control Switch Policy are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/node_control_policy/).



### Geolocation Policies




Geolocation is the identification of the geographic location of a networking device. This can be configured under: Fabric > Fabric Policies > Policies > Geolocation

Each Geolocation Policy contains a Tree, with Building, Floors, Room and Racks, where the ACI nodes are installed.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Geolocation must be defined in the input files:

<caption name="Geolocation Policy Data Model">

```yaml
apic:
  fabric_policies:
    geolocation:
      sites:
        - name: site1
          buildings:
            - name: building1
              floors:
                - name: floor1
                  rooms:
                    - name: room1
                      rows:
                        - name: row1
                          racks:
                            - name: rack1
                              nodes:
                                - 101
                                - 102
```
</caption>

For further info on how the Geolocation are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/geolocation/).



### MACSec Policies




MACsec is an IEEE 802.1AE standards-based Layer 2 hop-by-hop encryption that provides data confidentiality and integrity for media access independent protocols. This can be configured under: Fabric > Fabric Policies > Policies > Macsec

MACsec provides MAC-layer encryption over wired networks by using out-of-band methods for encryption keying. The MACsec Key Agreement (MKA) Protocol provides the required session keys and manages the required encryption keys. Only host facing links (links between network access devices and endpoint devices such as a PC or IP phone) can be secured using MACsec.

APIC distributes the MACsec keychain to all the nodes in a Pod or to ports on a node. Below are the supported MACsec keychain and MACsec policy distribution supported by the APIC.

- A single user provided keychain and policy per Pod
- User provided keychain and user provided policy per fabric interface
- Auto generated keychain and user provided policy per Pod



### Analytics Policies




This setting is used with Cisco Tetration Analytics. This can be configured under: Fabric > Fabric Policies > Policies > Analytics

The screen has information on the Cisco Tetration Analytics cluster server, along with the IP Address, port listened, and DSCP information. It has the name of the cluster along with the server policy name. The server policy name is attached to the switch policy-group of the leaf/TOR from which all packets are sent to the Cisco Tetration Analytics server.



## Tags



In ACI Tags can be defined and then associated to logical objects. Tags are a construct that allow a user to add some metadata against a group of objects so that these objects are grouped and can be queried under a single string name.




# marvel



Fabric Access Policies are policies that are used to control parameters related to Fabric Access, such as which VLAN range to use on a leaf and which Interface Policies to configure on fabric external-facing interfaces.



## Domains, Pools and AAEP



The chapter on ACI Access Policies - Domains, Pools, and AAEPs Demo content of how these components work together to define and manage network access within the ACI fabric. It explains that Domains specify the scope of VLAN pools applied to interfaces, VLAN Pools identify the VLANs used on interfaces, and Attachable Access Entity Profiles (AAEPs) link these domains and VLAN pools to physical random and interface policies, enabling consistent and controlled deployment of VLANs across the fabric. This chapter also covers the importance of mapping domains to ports via AAEPs to enforce policy and restrict VLAN usage, ensuring proper network segmentation and operational consistency.



### VLAN Pools



A pool represents a range of traffic encapsulation identifiers (for example, VLAN IDs, VNIDs, and multicast addresses). A pool is a shared resource and can be consumed by multiple domains such as physical domains, external routed domains, Virtual Machine Manager (VMM), etc.

Two types of VLAN-based pools exist.

- Dynamic pools - Dynamic pools are managed internally by the APIC to allocate VLANs for End Point Groups (EPGs). Dynamic pools are primarily used in combination with VMM integration.
- Static pools - Static pools are managed through the static configuration of EPG bindings. An EPG has a relation to the domain, and the domain has a relation to the pool. The pool contains a range of encapsulation VLANs. For static EPG deployments, it is required to define the interface and the encapsulation. The encapsulation must be within the range of a VLAN pool that is associated to a domain to which the EPG is associated.

A VLAN Pool is associated to one or multiple Encapsulation Blocks. An encapsulation block defines a VLAN Id Range.

There are three Allocation Modes for the Encapsulation Block:

- i wanna check this commet is properly preservin on that or not
- Static Allocation - when a VLAN is required, the user needs to statically choose it from the Block.
- Inherit allocMode from parent (default) - the mode at Encap level is taken from the mode set for the parent VLAN Pool.

The combination of VLAN Pool and Encapsulation block allocation mode configuration is translated into the following use cases:

- Encap Pool Static, Encap Block Static or Inherit : Non VMM integrated static paths. The VLAN is manually chosen by the user.
- Encap Pool Dynamic, Encap Block Dynamic or Inherit: VMM integration EPGs. VLAN is chosen by ACI from the pool, and the same VLAN is pushed to the virtual domain port-group.
- Encap Pool Dynamic, Encap Block Static: VMM Integration EPGs. VLAN is manually chosen from the pool by the user. The same VLAN is pushed to the virtual domain port-group.
- Encap Pool Static, Encap Block Dynamic: This is invalid configuration, and it will be blocked.

An Encapsulation Block has also a role:

- External or on the wire encapsulations-(Default): Used for allocating VLANs for each EPG assigned to the domain. The VLANs are used when packets are sent to or from leaf switches.
- Internal: Used for private VLAN allocations in the internal vSwitch by the Cisco ACI Virtual Edge (AVE). The VLANs are not seen outside the ESX host or on the wire.

Ranges of VLANs should be divided into blocks. VLAN blocks are the entities that can be added or deleted as a whole in the VLAN Pool. You cannot delete a single VLAN if this is part of a range in a VLAN block, you can only delete the entire block. Adding a VLAN block containing a single VLAN is also possible and there is no limitation in the amount of block that can be added.

VLAN Pools have a one-to-one relation with physical or virtual domains. Please refer to the domain guidelines.

In the %%customerName design, the following VLAN pools will be created:

<caption name="ACI-FABRIC-NAME - VLAN POOL Definition">

| VLAN Pool Name | Allocation Mode | Ranges |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how VLAN Pools need to be defined in the input files:

<caption name="VLAN Pools Data Model">

```yaml
apic:
  access_policies:
    vlan_pools:
      - name: STATIC1
        description: "Static VLAN Pool"
        allocation: static
        ranges:
          - from: 4000
            to: 4002
            role: external
            description: "Range #1"
```
</caption>

For further information on how VLAN Pools are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/vlan_pool/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.013">
VLAN ranges will be allocated in discrete blocks rather than pre-allocating the complete available range, allowing incremental expansion as needed.
<br><br>
Rationale: Cisco recommends allocating VLANs in smaller blocks because VLAN blocks are the atomic unit for addition and deletion within a VLAN pool. This approach provides operational flexibility for future expansion without requiring the removal and re-creation of large contiguous ranges.
</tip>
<br><br>




### Domains



In ACI, a domain represents a logical grouping that ties together physical and virtual networking components, policies, and configurations within the ACI fabric. There are four different domain types:

- Physical domains
- External bridged domains
- L3 domains External routed domains
- VMM domains

Different domain types are created depending on how a device is connected to the leaf nodes:

- Physical domains are generally used for bare metal servers and servers where hypervisor integration is not used.
- External bridged domains are used for Layer-2 connections. For example, an external bridge domain could be used to connect an existing switch trunk to a leaf switch. Typically, external bridge domain is used when two or more EPGs need to share the same Layer-2 connection.
- L3 Domain or External routed domains are used for Layer-3 connections.
- VMM Domains are used for hypervisor integration.
- Fibre Channel Domains used for FCoE F ports or NP ports connections.

Domains define available VLANs that can be consumed by a tenant EPG on a particular leaf port. Associating a VLAN pool to a domain creates this relationship.

Physical Domains can be defined per device groups (for example DC Firewall) or in relation to Security Domains (more information about Security Domains can be found in the Fabric Administration Chapter). There is a verified scalability limit of 10 domains per leaf switch.

Domains are configured under: Fabric - Access Policies - Physical and External Domains

In the %%customerName design, the following Domains will be created:

<caption name="ACI-FABRIC-NAME - Domain Name Domain Type Associated VLAN POOL">

| Domain Name | Domain Type | Associated VLAN POOL |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Domains need to be defined in the input files:

<caption name="Domains Data Model">

```yaml
apic:
  access_policies:
    physical_domains:
      - name: PHY1
        vlan_pool: ROUTED1
    routed_domains:
      - name: ROUTED1
```
</caption>

For further information on how Domains are defined in the IaC Data Model for ACI, please refer to the Network-as-Code (NaC) documentation for [Physical Domains](https://netascode.cisco.com/docs/data_models/apic/access_policies/physical_domain/) and [Routed Domains](https://netascode.cisco.com/docs/data_models/apic/access_policies/routed_domain/).



### AAEP



An Attachable Entity Profile (AEP) represents a group of external entities with similar infrastructure policy requirements.

The attachable access entity profile (AAEP) is used to map domains (physical or virtual) to interface policies; an AEP is required to deploy VLAN pools on leaf switches and it implicitly provides the scope of the VLAN pool to the physical infrastructure. AAEPs will be added to Interface Policy Groups.

As a concrete example, if vlan-100 belongs to the VLAN-Pool referenced by the AAEP-1, and AAEP-1 is associated to an Interface Policy-Group for interface Eth1/1 in Node-101, that means vlan-100 can now be used in Node-101. Vlan-200, conversely, cannot be used yet since it does not belong to that VLAN-Pool.

In addition, AAEPs allow a one-to-many relationship (if desired) to be formed between interface policy groups and domains as shown in the following figure:


<caption name="Attachable Access Entity Profile">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Attachable_Access_Entity_Profile.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


It is important to note that:

- The AEP defines the range of allowed VLANs, but it does not provision them.
- No traffic flows unless an EPG is deployed on the port.
- content has been chnages to you can see here only after replacemnt commets are properly preserving or not
- A particular VLAN is provisioned or enabled on the leaf port that is based on EPG events either statically binding on a leaf port or based on VM events from external controllers such as VMware vCenter or Microsoft Azure Service Center Virtual Machine Manager (SCVMM).

The AAEP can also be used to extend the infrastructure VLAN on a port.

In the %%customerName design, a separate AAEP will be defined for leaf ports connecting to servers and network devices, such as routers, firewalls, load balancers, etc., based on the type and purpose of the device that will be connected to that port.

The following AAEPs will be initially defined:

<caption name="AAEP Definition">

| AAEP name | Domain | Include infra VLAN | Usage |
| --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how AAEPs need to be defined in the input files:

<caption name="AAEP Data Model">

```yaml
apic:
  access_policies:
    infra_vlan: true
    aaeps:
      - name: AAEP1
        physical_domains:
          - PHY1
        routed_domains:
          - ROUTED1
        vmware_vmm_domains:
          - VMM1
        endpoint_groups:
          - tenant: ABC
            application_profile: AP1
            endpoint_group: EPG1
            vlan: 1234
            mode: untagged
            deployment_immediacy: immediate
```
</caption>

For further information on how AAEPs are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/aaep/).



### Guidelines for VLAN Pools, Domains and AEPs



In a traditional data center, a VLAN is spanned across a number of switches and devices to place the required end points in a single broadcast domain and/or Layer 3 subnet. In an ACI environment, the end points are placed in a single broadcast domain by having membership to an End Point Group (EPG) which in turn is placed on a specific Bridge Domain (BD).


<caption name="Non-overlapping VLANs">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Non-overlapping_VLANs.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


VLAN pools and Physical Domains are defined based on the type of physical device connecting to the ACI Fabric, for example a High Availability pair of Firewalls. In an EPG where multiple devices are statically bound, for example, Virtual Machines, Load Balancers, and Firewalls; each device type is bound with their own specific Domain which contains non-overlapping VLANs. The figure below exhibits the definition of non-overlapping VLAN pools per device type bound to a single EPG.

In scenarios where it is highly desired to use a single VLAN for binding of different device types to a single EPG; a common VLAN pool and a common Physical Domain can be additionally defined and associated with device specific AEPs.


<caption name="Common VLAN Pool and Physical Domain">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Common_VLAN_Pool_and_Physical_Domain.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


A common VLAN Pool and Physical Domain are used when the same VLAN identifier is required for binding multiple physical device types into a single EPG.



## Access Polices



Access policies enable the configuration of:

- Internal Facing Interfaces that connect to the hosts (virtual or physical), storage, firewalls and Fabric Extenders (FEXs).
- External Facing Interfaces that connect to the multi-pod/multi-site network devices and any routers/switches that are part of an outside network.
- Ports such as individual ports, port channels, and virtual port channels (vPC).
- Protocols such as Link Layer Discovery Protocol (LLDP), Cisco Discovery Protocol (CDP), and Link Aggregation Control Protocol (LACP).
- Features such as statistics gathering, monitoring, and diagnostics.


<caption name="Access Policies - Object Relationship">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Access_Policies-Object_Relationship.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


Access policies are grouped into the following categories:

- Switch Policies: specify which switches to configure and the switch configuration policy.
- Module Policies: specify which leaf switch access cards and access modules to configure and the leaf switch configuration policy.
- Interface Policies: specify which access interfaces to configure and the interface configuration policy.
- Global Policies: enable the configuration of DHCP, QoS, and attachable access entity (AEP) profile functions that can be used throughout the fabric. AEP profiles provide a template to deploy hypervisor policies on a large set of leaf ports and associate a Virtual Machine Management (VMM) domain and the physical network infrastructure. They are also required for Layer 2 and Layer 3 external network connectivity.
- Pools: specify VLAN, VXLAN, and multicast address pools. A pool is a shared resource that can be consumed by multiple domains such as VMM and Layer 4 to Layer 7 services. A pool represents a range of traffic encapsulation identifiers (for example, VLAN IDs, VNIDs, and multicast addresses).
- Physical and External Domains Policies:
- External bridged domain Layer 2 domain profiles contain the port and VLAN specifications that a bridged Layer 2 network connected to the fabric uses.
- External routed domain Layer 3 domain profiles contain the port and VLAN specifications that a routed Layer 3 network connected to the fabric uses.
- Physical Domain Policies contain physical infrastructure specifications, such as ports and VLAN, used by a tenant or endpoint group.
- Monitoring and troubleshooting Policies: specify what to monitor, thresholds, how to handle faults and logs, and how to perform diagnostics.

**Access Policies - Reuse**

Whereas a traditional command line interface on a switch generally requires a port-by-port configuration, ACI allows definition of objects and policies that can be reused. The reusability of these policies makes it possible to replicate the configuration of a switch very easily.


<caption name="Policy Reuse Comparison">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Policy_Reuse_Comparison.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


In a small data center, the configurations of a few switches do not require many processes or automation. As the data center size increases, automation becomes more and more critical as it has a direct impact on the cost of business operations.  In traditional networks, when significant changes affecting many devices are required, operators must invest time and resources in creating processes to manage those devices effectively. These can be network management tools, scripts, or specialized applications. By utilizing the Cisco ACI policy model, operators can use Fabric Access Policies to simplify the process of adding and managing devices. This is what is depicted as the policy re-use inflection point in the previous diagram.

<info name="Note">Virtual Port Channel Policy Groups cannot be reused. Every vPC requires its dedicated Policy Group.</info>

The following design decisions have been made in this section:

<tip name="Design Decision DD.014">
Fabric Access Policies will be standardised and re-used across the deployment wherever possible.
<br><br>
Rationale: Cisco recommends standardising and reusing access policies to simplify switch onboarding, reduce configuration drift, and lower the operational cost of managing a growing number of fabric nodes. Reusable policies ensure consistent behaviour across all leaf and spine switches.
</tip>
<br><br>




## Interfaces



The chapter on Interfaces in Access Policies provides an overview of the configuration and policies applied to leaf switch interfaces that connect to edge devices in the Cisco ACI fabric. It covers key elements such as interface policies (including VLAN scope, LACP, LLDP, CDP), interface profiles, port channels, and virtual port channels, which are essential for managing physical connectivity and ensuring consistent policy enforcement at the fabric edge. This chapter also explains how interface policy groups and profiles are used to define interface settings and how these are linked to VLAN pools and attachable access entity profiles (AAEPs) to enable scalable and reusable access layer configurations across the fabric.


The Interface Policy Groups collect all the interface policies required for the specific connectivity.

An Interface Profile can be seen as a container for interface selectors.

Interface Selectors are used to select an individual port or port ranges and to associate those with an Interface Policy Group.

Interface Profiles are then associated to Switch Profiles in order to link ports and their Interface Policy Group to switches.

Distinct Interface Profiles are created for Leaf Switches and Spine Switches.


<caption name="Interface Profile Object Relationship">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Interface_Profile_Object_Relationship.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### Interface Policy Groups



Interface Policy Groups are templates used to dictate ports behavior. Interface policy groups use the interface policies described in previous section to specify how links should behave.

An Interface policy group is also associated to an AAEP and to a switch port through Interface selector. This double association (AAEP and interface) will result in associating a set of domains and their VLAN Pool to a switch interface.

There are three types of interface policy groups depending on link type:

- Access Ports (individual)
- Port channel
- Virtual Port Channel (vPC)

The type of interface policy groups will have an impact on how it will be used within the ACI Fabric.

A unique interface policy group should be defined for each port channel and virtual port channel, as an interface policy is the triggering object for generating a port-channel interface when the configuration is applied to the leaf nodes. Each host connected to the ACI Fabric by means of a vPC or a Port-Channel will require a unique vPC or PC Policy Group.

An access port policy group can be reused for all interfaces having the same Interface policy and AAEP requirements.

A Port-channel Interface policy group is associated to a single switch profile, whereas vPC interface policy-groups need to be associated to two switches, which in turn form the vPC domain.

In the %%customerName ACI design, the Interface Policy Group configuration will follow these guidelines:

- One Access Interface Policy Group per type of bare metal device and connectivity settings. This will be reused for all links with similar configuration options.
- One Port-Channel Interface Policy Group per Port-Channel interface, as they cannot be reused.
- One vPC Interface Policy Group per vPC interface, as they cannot be reused.

The Interface Policy Group will define the list of interface policies to be used for the port, such as link speed, CDP policy, STP policy, storm control policy to be applied. You must also associate the Interface Policy Group with the AEEP that contains the domain(s) with their corresponding VLAN pools, from which a VLAN can then be derived when the port is bound to an End Point Group.

The following table shows the Interface Policy Groups that are foreseen for the initial implementation of the %%customerName fabric.

<caption name="ACI-FABRIC-NAME - Sample Leaf Access and vPC PC Interface Policy Group">

| Name | Description |
| --- | --- |
</caption>

<note name="Note">A full list of the required Interface Policy Groups is included in the NIP.</note>

Leaf and Spine switches use distinct interface policy-group types. Spine switches currently only support Access Port policy groups.



#### Leaf Access Ports Interface Policy Groups



An Access Port Interface policy group can be potentially reused by Hosts sharing the same connectivity requirements (Interface policies) and AAEP attachment.

For the %%customerName ACI design, the naming convention for the Leaf Access Port Interface Policy Groups will be: ACC_[purpose]_IPG

Where, purpose is the type of server or end host that connects to the ACI fabric without link aggregation.

For instance, if Server 2, Server 3, and Server 5 are each either single or dual homed, and don't require Link Aggregation, then, potentially, a single Access IPG could be used for all connections:

- ACC_SERVER_IPG


<caption name="Access Interface Policy Groups example">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Access_Interface_Policy_Groups_example.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


The following table shows the values of one Access Interface Policy Group that will be defined in the %%customerName design:

<caption name="ACI-FABRIC-NAME - Access Port Interface Policy Group">

| Policy Group Name | AAEP | Link Level Policy | CDP Policy | LLDP Policy | Spanning Tree Policy |
| --- | --- | --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Access Leaf Interface Policy Groups need to be defined in the input files:

<caption name="Access Ports Interface Policy Group Data Model">

```yaml
apic:
  access_policies:
    leaf_interface_policy_groups:
      - name: SERVER1
        description: Server1
        type: access
        link_level_policy: 10G
        cdp_policy: CDP-ENABLED
        lldp_policy: LLDP-ENABLED
        spanning_tree_policy: BPDU-FILTER
        mcp_policy: MCP-ENABLED
        l2_policy: PORT-LOCAL
        storm_control_policy: 10P
        port_channel_policy: LACP-ACTIVE
        port_channel_member_policy: FAST
        aaep: AAEP1
```
</caption>

For further information on how Access Leaf Interface Policy Groups are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_leaf_interface_policy_group/).



#### Leaf Virtual Port Channel and Port Channel Policy Groups



One virtual Port-Channel (vPC) or Port-channel Interface Policy-group will be created per vPC connected to a host.

One ad-Hoc vPC/PC Interface Policy Group will be used per device connected to the ACI Fabric.

For the %%customerName ACI design, the naming convention for the vPC/PC Interface Policy Groups will be: 

IPG type:

- VPC = Virtual Port Channel Interface Policy Group
- PC = Port Channel Interface Policy Group

For instance, if Server 1 and Server 7 are both dual homed and require Link Aggregation and LACP, then two separate vPC/PC IPGs are needed:

- VPC_SRV1_IPG
- VPC_SRV7_IPG


<caption name="vPC Interface Policy Groups example">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/vPC_Interface_Policy_Groups_example.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


The following table shows the values of a sample vPC Interface Policy Group that could be defined in the %%customerName design:

<caption name="ACI-FABRIC-NAME - vPC Interface Policy Groups">

| Name | Link Level | CDP Policy | LLDP Policy | AAEP | Port-channel Policy | MCP Policy | Storm Control | STP Policy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
</caption>

<note name="Note">One separate vPC/PC Interface Policy Group will be defined for each end host that requires link aggregation. This type of Interface Policy Groups cannot be reused.</note>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how VPC Leaf Interface Policy Groups need to be defined in the input files:

<caption name="Virtual Port Channel Policy Group Data Model Example">

```yaml
apic:
  access_policies:
    leaf_interface_policy_groups:
      - name: IPG_VPC_LEGACY_POD1
        type: vpc
        link_level_policy: LINK_AUTO_AUTO
        port_channel_policy: LACP_ACTIVE
        cdp_policy: CDP_ENABLE
        lldp_policy: LLDP_ENABLE
        spanning_tree_policy: BPDU_PASS
        l2_policy: GLOBAL_SCOPE
        mcp_policy: MCP_DISABLE
        aaep: AEP_PHY_LEGACY
```
</caption>

For further information on how VPC Leaf Interface Policy Groups are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_leaf_interface_policy_group/).



#### Spine Interface Policy Groups



Just like for Leafs, a Spine Access Port Interface Policy Group can be reused for spine links that have the same connectivity requirements (Interface policies) and AAEP attachment.

For the %%customerName ACI design, the naming convention for the Spine Access Port Interface Policy Groups will be following: ACC_SPINE_[device]_IPG.

Where, device is the network device connected to the spine, such as an IPN node.

The following table shows the values of one Spine Interface Policy Group that will be defined in the %%customerName design:

<caption name="ACI-FABRIC-NAME - Spine Interface Policy Group">

| Name | CDP | AAEP | Link-Level Policy |
| --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Spine Interface Policy Groups need to be defined in the input files:

<caption name="Spine Interface Policy Group Data Model Example">

```yaml
apic:
  access_policies:
    spine_interface_policy_groups:
      - name: IPG_ACP_SPINE1_IXN
        cdp_policy: CDP_ENABLE
        aaep: AEP_L3D_IXN
        link_level_policy: LINK_100G_STATIC
```
</caption>

For further information on how Spine Interface Policy Groups are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_spine_interface_policy_group/).



### Interface Profiles



Interface Profiles contain blocks of ports, identified by interface selectors, and tie the selectors to interface policy groups. Before the ports defined in the interface port profile/selector are assigned to actual host-facing interfaces on a leaf, the interface port profile must be associated with a switch profile.



### Leaf Interface Profile



One way of creating Interface Profiles and Interface Selectors, which offers flexibility and can be easily automated, is to define one Interface Profile per Leaf switch.

The interface profile will be then easily associated to the corresponding leaf switch profile. Each time a leaf node port is required, an interface selector will be created within the interface profile and the corresponding interface policy group will be associated.

The interface profile will use the following naming convention: [&#39;node-ID&#39;]

<caption name="ACI-FABRIC-NAME - Leaf Interface Profiles">

| Interface Profile | Description |
| --- | --- |
</caption>

The next table is an example for the Interface Selectors that can be defined in the Interface Profiles:

<caption name="ACI-FABRIC-NAME - Sample Interface Selectors">

| Interface Profile | Interface Selector | Port Blocks | Associated IPG |
| --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Leaf Interface Profiles need to be defined in the input files:

Auto-generated profiles

<caption name="Leaf Interface Profile Data Model - Auto-Generated">

```yaml
apic:
  auto_generate_switch_pod_profiles: true
  access_policies:
    leaf_interface_profile_name: "LEAF\\g<id>"
```
</caption>

Explicitly defined profiles

<caption name="Leaf Interface Profile Data Model - Explicitly Defined">

```yaml
apic:
  access_policies:
    leaf_interface_profiles:
      - name: LEAF1001
        selectors:
          - name: SEL1
            policy_group: 10G-SERVER
            port_blocks:
              - name: BLOCK1
                description: Server ABC
                from_port: 1
```
</caption>

For further information on how Leaf Interface Profiles are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_leaf_interface_profile/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.015">
One Leaf Interface Profile will be created per leaf switch in a one-to-one relationship, following Cisco best practice for flexibility and automation.
<br><br>
Rationale: Defining one interface profile per leaf switch avoids the confusion that arises from shared profiles and ensures each switch can be independently configured. This one-to-one approach is considered best practice because it simplifies automation, prevents unintended configuration overlap, and scales cleanly as new leaf nodes are added.
</tip>
<br><br>




### Spine Interface Profile



Spine Interface Profiles are needed for extending VXLAN to other sites in Multi-Pod, Multi-Site or Remote Leaf solutions.

One Spine Interface Profile will be created for every spine node. The Spine Interface Profile will use the following naming convention: [&#39;node-ID&#39;]

The Spine interface profile will be associated to the corresponding spine switch profile. Each time a spine node port is required, an interface selector will be created within an interface profile and the corresponding interface policy group will be associated.

<caption name="ACI-FABRIC-NAME - Spine Interface Profiles">

| Interface Profile | Description |
| --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Spine Interface Profiles need to be defined in the input files:

Auto-generated profiles.

<caption name="Spine Interface Profile Data Model - Auto-Generated">

```yaml
apic:
  auto_generate_switch_pod_profiles: true
  access_policies:
    spine_interface_profile_name: "SPINE\\g<id>"
```
</caption>

Explicitly defined profiles.

<caption name="Spine Interface Profile Data Model - Explicitly Defined">

```yaml
apic:
  access_policies:
    spine_interface_profiles:
      - name: SPINE101
        selectors:
          - name: SEL1
            policy_group: IPN
            port_blocks:
              - name: BLOCK1
                description: IPN1
                from_port: 1
```
</caption>

For further information on how Spine Interface Profiles are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_spine_interface_profile/).



## Polices



The Policies sub-chapter in Cisco ACI Interfaces configuration covers settings applied to physical and logical interfaces, including protocols like CDP, LLDP, and link speed. These policies standardize interface behavior across the fabric by managing features such as protocol enablement and link parameters through named policy groups.



### Switch Policies







### vPC Domain




In the ACI fabric the vPC MCT (MultiChassis etherChannel Trunk) communication happens through the fabric. The ACI Leaf detects its vPC peer down when the vPC-peer route is withdrawn by ISIS. The vPC domain policy is applied to both vPC devices and it allows setting the "Peer Dead Interval," which by default is 200 seconds. 

If all the fabric links for the leaf participating as a vPC peer go down, the vPC manager brings down all its vPCs. This action is taken to prevent dual active scenarios. When the first fabric link comes back up, the vPC manager starts the restore times. If the peer does not come up within the dead interval, it brings up all its vPCs.

The vPC domain policy is applied to the vPC protection group.

The %%customerName design will use the default values for the vPC domain policy.

The following design decisions have been made in this section:

<tip name="Design Decision DD.016">
The vPC domain policy will use default values, including the peer dead interval of 200 seconds.
<br><br>
Rationale: Cisco recommends leaving the peer dead interval at the default 200 seconds for stability. Reducing this timer without a specific high-convergence requirement risks premature vPC failovers caused by transient control-plane events, which can lead to unnecessary traffic disruption.
</tip>
<br><br>




### vPC Protection Group




The vPC Port-Channel Security Policy is responsible for creating the vPC Protection Groups. The vPC protection groups define the different pairs of switches that will form a vPC domain.

Each vPC Protection Group must have a Name and an ID, called Logical Pair ID.

The definition of switch pairs can be done in multiple ways (Explicit and automatic):

- Explicit allows the user to define the nodes to use as vPC pair.
- Automatic can be Consecutive pairing, every two leaves will form a vPC pair (for example 149 and 150), or it can be reciprocal pairing, every consecutive odd node and even nodes (for example 149 and 151 is one vPC pair and 150 and 152 is another vPC pair).

The Logical Pair ID of the vPC protection group will be explicit and will be the last 3 digits of the Odd Node ID in the VPC pair.

```text
101
```

The Logical ID for the VPC pair of nodes 1103 and 1104:

```text
103
```

The Name of the vPC Protection Group will use this naming convention: VPC_[node-1]_[node_2]

<caption name="vPC Protection Group parameters">

| Parameter | Value |
| --- | --- |
| Protection Group Name | VPC_[node-1]_[node_2] |
| Logical Pair ID | Value between 1 and 1000 |
| vPC Domain Policy | Default |
| Switch One (left switch) | Odd Switch Node ID |
| Switch Two (right switch) | Even Switch Node ID |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how VPC Protection Groups need to be defined in the input files:

<caption name="vPC Protection Group Data Model">

```yaml
apic:
  node_policies:
    vpc_groups:
      mode: explicit
      groups:
        - id: 101
          switch_1: 101
          switch_2: 102
```
</caption>

For further information on how VPC Protection Groups are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/node_policies/vpc_group/).

<note name="Note">The full list of explicit protection group definitions is provided in the Network Implementation Plan document (NIP).</note>

The following design decisions have been made in this section:

<tip name="Design Decision DD.017">
Explicit pairing will be used for vPC Protection Groups, with the Logical Pair ID derived from the odd node ID of the vPC pair.
<br><br>
Rationale: Cisco recommends explicit pairing over automatic pairing to ensure deterministic vPC domain assignments. Explicit pairing prevents unintended node combinations that can occur with automatic methods and provides clear, auditable switch-pair definitions that align with physical cabling.
</tip>
<br><br>




### Interface Policies




Interface policies are used to dictate fabric access interface behavior. They are categorized into types based on the category of property or protocol they are acting on.

Interface policies are later referenced by an "Interface Policy Group." That Interface Policy Group is then applied to specific Interfaces and Switches.

The following interface Policy Types are available:

- Link Level
- CDP Interface
- LLDP Interface
- Port-Channel
- Port-Channel Member
- Spanning-Tree Interface
- MCP Interface
- Storm Control
- L2 Interface Policy
- Port Security
- Data Plane Policing
- 802.1x Port Authentication
- MACSec
- PoE
- Netflow
- CoPP

The following interface Policies are specific to Fibre Channel Configuration

- Fibre Channel Interface
- Priority Flow Control
- Slow Drain

The DWDM interface policy is used to tune DWDM optics to a specific DWDM port channel number.

The following design decisions have been made in this section:

<tip name="Design Decision DD.018">
A comprehensive set of interface policies will be pre-created covering the different configuration options for each policy type, with policy names that clearly describe their purpose.
<br><br>
Rationale: Cisco recommends creating interface policies that cover the range of expected configurations (e.g., CDP enabled/disabled, various link speeds) and using descriptive naming conventions. This pre-creation enables rapid, consistent deployment of new interfaces without ad-hoc policy creation and reduces misconfiguration risk.
</tip>
<br><br>




### Link Level Policies




The Link Level Policies dictate link level configuration such as:

- Interface Speed and Auto-Negotiation.
- Link de-bounce Time.
- Forwarding Error Correction.

In the %%customerName ACI design the following Link Level Policies will be configured in each fabric:

<caption name="ACI-FABRIC-NAME - Link Level Policies">

| Name | Speed | Auto Negotiation | De-bounce Interval | FEC |
| --- | --- | --- | --- | --- |
</caption>

It is common to use specific policies without negotiation enabled if it is known what the interface link speed is. For example, 10Gig; instead of 10gigAuto.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Link Level Interface Policies need to be defined in the input files:

<caption name="Link Level Policies Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      link_level_policies:
        - name: 10G
          speed: 10G
          auto: true
          fec_mode: inherit
```
</caption>

For further information on how Link Level Interface Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/link_level_policy/).



### CDP Policies




The CDP interface policy is primarily used to obtain protocol addresses of neighboring devices and discover the platform of those devices. CDP can also be used to display information about the interfaces your router uses. CDP is media-and protocol-independent and runs on all Cisco-manufactured equipment including routers, bridges, access servers, and switches.

The administrative state can be:

- Enabled
- Disabled

The default is Disabled.

The CDP Policy dictates the Access Interface configuration for the Cisco Discovery Protocol.

In the %%customerName ACI design these CDP Policies will be configured in each fabric:

<caption name="ACI-FABRIC-NAME - CDP Policies">

| Name | Admin state |
| --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how CDP Interface Policies need to be defined in the input files:

<caption name="CDP Policies Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      cdp_policies:
        - name: CDP-ENABLED
          admin_state: true
```
</caption>

For further information on how CDP Interface Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/cdp_policy/).



### LLDP Policies




The LLDP interface policy defines a common configuration that will apply to one or more LLDP interfaces. LLDP uses the logical link control (LLC) services to transmit and receive information to and from other LLDP agents.

The following Enable and Disable options exist:

- Receive State
- Transmit State

The default is Disabled.

The LLDP Policy dictates the Access Interface configuration for the Link Layer Discovery Protocol.

In the %%customerName ACI design these LLDP Policies will be configured in each fabric:

<caption name="ACI-FABRIC-NAME - LLDP Policies">

| Name | Receive state | Transmit state |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how LLDP Interface Policies need to be defined in the input files:

<caption name="LLDP Policies Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      lldp_policies:
        - name: LLDP-ENABLED
          admin_rx_state: true
          admin_tx_state: true
```
</caption>

For further information on how LLDP Interface Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/lldp_policy/).



### Port Channel Policies




The Port Channel policy dictates the physical port bundling characteristics such as:

- Mode: Static, LACP Active (Default), LACP Passive, MAC Pinning
- LACP Control such as
- Fast Select Hot Standby Ports
- Graceful Convergence
- Suspended individual
- Port-Channel Min-Link and Max-Link

In the %%customerName ACI design these Port channel policies will be configured in each fabric:

<caption name="ACI-FABRIC-NAME - Port Channel Policies">

| Name | Mode | Min. link | Max. link | Control |
| --- | --- | --- | --- | --- |
</caption>

The default enabled control features with LACP are:

- Fast Select Hot Standby Ports - Allow fast selection of a hot standby port when last active port in the port-channel is going down.
- Graceful Convergence - Enables LACP graceful convergence.
- Suspend Individual Port - Sets a port to the suspend state if it does not receive an LACP PDU from the peer port in a port channel. This can cause some servers to fail boot up, as they require LACP to locally bring up the port (only applicable to servers directly connected to a leaf node).

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Port Channel Interface Policies need to be defined in the input files:

<caption name="Port Channel Policies Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      port_channel_policies:
        - name: LACP-ACTIVE
          mode: active
```
</caption>

For further information on how Port Channel Interface Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/port_channel_policy/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.019">
LACP Active mode will be used as the default port-channel policy, with the default control features (Fast Select Hot Standby Ports, Graceful Convergence, Suspend Individual Port) enabled unless explicitly required otherwise by connected devices.
<br><br>
Rationale: Cisco recommends enabling the default LACP control features to provide fast failover, graceful convergence during link transitions, and protection against miscabled single links. Suspend Individual may be disabled only for servers that require the port to be up before LACP negotiation completes, such as during PXE boot.
</tip>
<br><br>




### Port Channel Member Policies




The Port Channel Member policies dictate the LACP Transmit rate and LACP Interface Priority. The transmit rate dictates the periodicity of LACP packets. Fast send LACP packets every second, Normal every 30 seconds. The Interface Priority dictates what interfaces should be active and what should be placed in standby if not all links are necessary.

In the %%customerName ACI design these Port Channel Member policies will be configured in each fabric:

<caption name="ACI-FABRIC-NAME - Port Channel Member Policies">

| Name | Priority | Transmit Rate |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Port Channel Member Policies need to be defined in the input files:

<caption name="Port Channel Member Policies Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      port_channel_member_policies:
        - name: FAST
          rate: fast
          priority: 32768
```
</caption>

For further information on how Port Channel Member Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/port_channel_member_policy/).



### Spanning Tree Interface Policies




The Spanning Tree Interface dictates the configuration of the BPDU Guard and BPDU Filter features on an interface.

In the %%customerName ACI design these Spanning Tree policies will be configured in each fabric:

<caption name="ACI-FABRIC-NAME - Spanning Tree Interface Policies">

| Name | BPDU Filter | BPDU Guard |
| --- | --- | --- |
</caption>

An ACI fabric does not participate in spanning-tree, instead STP BPDUs received on a given port/VLAN will be flooded on all other ports associated with the same End Point Group (EPG) and VLAN, even if the VLANs are associated with EPGs in different Bridge Domains. This flooding behavior allows the ACI fabric to appear as a wire to the network devices attached to the ACI fabric.

If an MST region is connected to the ACI fabric, a special configuration is required for the ACI fabric to forward the MST BPDUs to other ports in the same BD.

There are some considerations when connecting external L2 networks to an ACI fabric. For instance, if an STP TCN (Topology Change Notification) is received by an ACI fabric, all the End Points in the same EPG will be flushed. If, for instance, the external L2 switch has the wrong configuration for one or more server ports and the network adapters of those servers go up and down frequently, a TCN would be sent by the switch and received by the ACI fabric every time that happens, forcing the necessity to re-learn all the endpoints in that EPG. This would naturally cause disruption in the network. To prevent this, if there are no potential L2 loops in the topology, BPDU Filter could be applied on the port.

The BPDU Filter approach can be taken, as long as it can be guaranteed that all the external L2 switches that will be connected to each ACI fabric will never be connected to each other via L2 and that each one of those switches will have only one single logical L2 connection to the ACI fabric (via PC or vPC). Refer to the L2 Extension section for more details.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Spanning Tree Interface Policies need to be defined in the input files:

<caption name="Spanning Tree Interface Policies Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      spanning_tree_policies:
        - name: BPDU-FILTER
          bpdu_filter: true
```
</caption>

For further information on how Spanning Tree Interface Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/spanning_tree_policy/).



### Storm Control Policies




In the %%customerName ACI design, these Storm Control policies will be initially defined:

<caption name="ACI-FABRIC-NAME - Storm Control Policies">

| Name | Rate type | Rate | Max. burst | Description |
| --- | --- | --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Storm Control Interface Policies need to be defined in the input files:

<caption name="Storm Control Policies Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      storm_control_policies:
        - name: 10P
          alias: 10P
          broadcast_burst_pps: unspecified
          broadcast_pps: unspecified
          broadcast_burst_rate: 10
          broadcast_rate: 10
          multicast_burst_pps: unspecified
          multicast_pps: unspecified
          multicast_burst_rate: 10
          multicast_rate: 10
          unknown_unicast_burst_pps: unspecified
          unknown_unicast_pps: unspecified
          unknown_unicast_burst_rate: 10
          unknown_unicast_rate: 10
          action: drop
```
</caption>

For further information on how Storm Control Interface Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/storm_control_policy/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.020">
Storm Control policies will be pre-defined but not initially associated to any Interface Policy Groups until a traffic baseline has been established.
<br><br>
Rationale: Cisco recommends creating Storm Control policies upfront but deferring their application until after a baseline of normal broadcast, multicast, and unknown unicast traffic levels has been observed. Premature enforcement without a baseline risks dropping legitimate traffic and causing application outages.
</tip>
<br><br>




### L2 Interface Policies




L2 Interface Policies are used to define the scope of a VLAN on the host-facing interfaces. The available scopes are:

- Global - Sets the VLAN encapsulation value to map only to a single EPG per leaf.
- Port - Sets the Port + VLAN encapsulation combination to map to an EPG, which essentially enables the same VLAN to map to different EPGs when deployed on different ports.

If Port scope is chosen, it is required to use the same VLAN ID in the same leaf on different EPGs, that:

- The EPGs belong to different Bridge Domains.
- The EPGs have different physical domains attached and those domains use different VLAN pools.

In addition, the L2 Interface Policy specifies the interface QinQ characteristics:

- disabled
- corePort
- doubleQtagPort
- edgePort

<caption name="ACI-FABRIC-NAME - L2 Interface Policies">

| Name | VLAN Scope | QinQ |
| --- | --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how L2 Interface Policies need to be defined in the input files:

<caption name="L2 Interface Policies Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      l2_policies:
      - name: PORT-LOCAL
        vlan_scope: portlocal
        qinq: disabled
```
</caption>

For further information on how L2 Interface Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/l2_policy/).



### MCP Interface




The mis-cabling protocol (MCP) is designed to handle misconfigurations that Link Layer Discovery Protocol (LLDP) and Spanning Tree Protocol (STP) are unable to detect.

MCP utilizes a Layer 2 packet and disables ports that create loops within the fabric. The untagged MCP packet is transmitted, and if the fabric detects that the packet returns, it identifies a loop and takes appropriate action. This event triggers the generation of faults and alerts.

The MCP Interface Policy enables or disables the MCP state at the interface level.

MCP can be enabled globally and per-interface. By default, MCP is disabled globally and is enabled on each port. For MCP to work, it must be enabled globally, regardless of the per-interface configuration. MCP must be enabled both globally and at the interface level in order to be active.

In the %%customerName ACI design, per-VLAN MCP will be enabled on ports connected to server enclosures. It will not be enabled on firewalls, load balancers, routers, switches, appliances, etc.

In the %%customerName design, the following MCP Interface policies will be defined:

<caption name="ACI-FABRIC-NAME - MCP Interface Policies">

| Name | Admin State |
| --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how MCP Interface Policies need to be defined in the input files:

<caption name="MCP Interface Data Model">

```yaml
apic:
  access_policies:
    interface_policies:
      mcp_policies:
      - name: MCP-ENABLED
        admin_state: true
```
</caption>

For further information on how MCP Interface Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/mcp_policy/).



### MACSec Policy




MACsec is an IEEE 802.1AE standards-based Layer 2 hop-by-hop encryption that provides data confidentiality and integrity for media access independent protocols. APIC allows users to program MACsec keys and MACsec configuration for Ethernet interfaces on the fabric on a per physical interface basis.

MACsec provides MAC-layer encryption over wired networks by using out-of-band methods for encryption keying. The MACsec Key Agreement (MKA) Protocol provides the required session keys and manages the required encryption keys. Only host facing links (links between network access devices and endpoint devices such as a PC or IP phone) can be secured using MACsec.

In the %%customerName design, MACsec will not be used.



### Global Policies







### Attached Entity Profile




The Attachable Access Entity Profiles (AAEPs) provide the association between physical and/or virtual domains and the physical network infrastructure and/or Virtual Machine Management (VMM).

AAEPs can be considered the "where" of the fabric configuration and are used to group domains with similar requirements. AAEPs are tied to interface policy groups. One or more domains are added to an AAEP. By grouping domains into AAEPs and associating them, the fabric knows where the various devices in the domain live and the APIC can push the VLANs and policy where it needs to be.

The decision of how many AAEP is required depends on many factors. Typically, a reduced number of AAEP is desired for simplicity, but there are some scenarios where multiple separated AAEP are required, including but not limited to the following situations:

- If the infrastructure VLAN has to be enabled on some ports, then a different AAEP is used for those particular interfaces. Extending the infra VLAN is only required for some VMM integration options beyond the virtual switch.
- The AAEP contains relationships to the virtual switch policies, which are then pushed to the virtual switch. If there are multiple VMM domains deployed with different virtual switch policies, multiple AAEPs are created to account for the different virtual switch policy combinations.

<note name="Note">In an SCVMM integration, ACI sees each Hyper-V host as a Leaf, a VTEP, therefore it needs to know the infrastructure Vlan.</note>

Refer to the Domains, Pools and AAEP section previously in this chapter for more details.



### QOS Class Policies




QoS within ACI deals with classes and markings to place traffic into these classes. Each QoS class represents Class of Service and is equivalent to "qos-group" in traditional NX-OS. Each Class of Service maps to a Queue in Hardware.

The Class of Service can be configured with various options, including a Scheduling Policy (Weighted Round Robin or Strict Priority, WRR being default), Min Buffer (guaranteed buffer).

These classes are configured at a system level and are therefore called System Classes. At the system level, there are 6 supported classes:

- A maximum of 6 "User-defined" classes.
- 3 "Reserved" classes which are not configurable by the user. These are used for control plane traffic and SPAN traffic.

The three user defined classes are:

- Level 1
- Level 2
- Level 3 (default class enabled by default).

Starting with release 4.0(1x), QoS supports levels 4, 5, and 6.

The following limitations apply:

- Number of classes that can be configured with Strict priority is up to 5.
- The 3 new classes are not supported with non-EX and non-FX switches.
- If traffic flows between non-EX or non-FX switches and EX or FX switches, the traffic will use QoS level 3.
- For communicating with FEX for new classes, the traffic carries a Layer 2 COS value of 0.

<note name="Note">In previous ACI releases, only 1 of the first 3 classes could be set as a "Strict Priority" class.</note>

These QoS classes are configured for all ports in the fabric (Leaf, Spine, ASIC, and internal port). There is no per-port configuration of QoS Classes in ACI.

In the %%customerName design, the user defined QoS Classes will be configured as follows:

<caption name="User Defined QoS Classes - default values">

| Queue | Level 1 | Level 2 | Level 3 (Default) | Level 4 | Level 5 | Level 6 |
| --- | --- | --- | --- | --- | --- | --- |
| Admin State | Disabled | Disabled | Enabled | Disabled | Disabled | Disabled |
| Priority Flow Control Admin State | false | false | false | false | false | false |
| No-Drop-Cos | | | | | | |
| MTU | 9216 | 9216 | 9216 | 9216 | 9216 | 9216 |
| Minimum Buffers | 0 | 0 | 0 | 0 | 0 | 0 |
| Congestion Algorithm | Tail Drop | Tail Drop | Tail Drop | Tail Drop | Tail Drop | Tail Drop |
| Scheduling Algorithm | Weighted Round Robin | Weighted Round Robin | Weighted Round Robin | Weighted Round Robin | Weighted Round Robin | Weighted Round Robin |
| Bandwidth Allocated (in %) | 20 | 20 | 20 | 0 | 0 | 0 |
</caption>

At the time of this writing, the following parameters are not configurable:

- Congestion Notification (ECN): Fixed to Disabled
- Queue Control Method: Fixed to Dynamic
- Queue Limit: 1522 bytes.

In the QoS class policy configuration there is also the option to preserve Cos Dot1p value. The 'Preserve Cos Dot1p' option is disabled by default (option unchecked).

By default, the Cos Dot1p marking of the original ingress frame is not preserved. Cos Dot1p marking of frames egressing the ACI fabric is set to 0.

By enabling, 'Preserve Cos Dot1p', the Cos Dot1p value of the received frame is mapped to DSCP field in the VXLAN Header. And at egress the Cos Dot1p value is mapped back from DSCP field in the VXLAN Header.

The Preserve Cos Dot1p option is not compatible with configuring DSCP class-cos translation policy in Tenant Infra, because both configurations use the DSCP field in the VXLAN Header. DSCP class-cos translation policy in Tenant Infra configuration is done with Multi-Pod/Multi-Site deployment, to prioritize ACI control traffic across the IPN/ISN geographical network.

In the %%customerName design, the DSCP class-cos translation policy in Tenant Infra will be used for Multi-Pod. Refer to the Multi-Pod section for more details.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how QoS Class Policies need to be defined in the input files:

<caption name="QOS Class Policies Data Model">

```yaml
apic:
  access_policies:
    qos:
      preserve_cos: false
      qos_classes:
        - level: 1
          scheduling: strict-priority
          congestion_algorithm: tail-drop
        - level: 2
          scheduling: wrr
          bandwidth_percent: 20
          congestion_algorithm: wred
```
</caption>

For further information on how QoS Class Policies are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/qos/).



### MCP Global Policy




The ACI fabric does not participate in the Spanning Tree Protocol (STP). Instead, it implements the mis-cabling protocol (MCP) to detect loops.

The Mis-Cabling Protocol (MCP) is a new link level loopback packet that detects an external L2 forwarding loop.

- MCP frames are originated on LEAF Host Facing ports (which are enabled for MCP).
- MCP frames are tagged with Fabric specific info (key).
- If any leaf node detects MCP packet arriving on a port that originated from the same fabric the port is err-disabled.

<note name="Note">For MCP to be effective it needs to be configured both globally and at the interface level through a specific MCP Interface policy</note>

By default, MCP runs in native VLAN mode where the MCP PDUs sent are not VLAN tagged. With this setting, MCP can detect loops due to mis-cabling if the packets sent in the native VLAN are received by the fabric. However, if there was a loop in non-native EPG VLANs, then it would not be detected. Starting with release 2.1(1), the APIC supports sending MCP PDUs per VLAN.

In the %%customerName design, the global MCP policy will be defined like this:

<caption name="MCP Instance Policy Default">

| Parameter | Value |
| --- | --- |
| Admin state | enabled |
| Enable MCP BPDU per VLAN | checked |
| Key | <intentionally omitted> |
| Initial Delay | 180 sec |
| Loop Detect Multiplication Factor | 3 |
| Loop Protection Action | Port Disable |
| Transmission Frequency | 2 sec |
</caption>

The key is a password used to uniquely identify the MCP packets within this fabric.

The Initial Delay sets the time that the system has to wait before the MCP starts taking action based on the value of the Loop Protection Action. From the system boot-up until the Initial Delay times out, MCP will only create a syslog entry if a loop is detected. The range is from 0 to 1800 seconds. The default is 180 seconds.

The Loop Detect Multiplication Factor is the multiplication factor that MCP uses to determine when a loop is formed. It denotes the number of continuous packets a port has to receive before claiming a loop is formed. The range is from 1 to 255. The default is 3.

The Loop Protection Action determines how MCP acts when a loop is detected. MCP error-disables the port or syslog only based on this value. The default is Port Disabled.

The Transmission Frequency (sec) sets the transmission frequency of the instance advertisements. The range is from 2 to 300 seconds. The default is 2 seconds.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Global MCP Policy needs to be defined in the input files:

<caption name="MCP Global Policy Data Model">

```yaml
apic:
  access_policies:
    mcp:
      action: false
      admin_state: true
      key: cisco
      frequency_sec: 5
      initial_delay: 300
      loop_detection: 5
      per_vlan: false
```
</caption>

For further information on how the Global MCP Policy is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/mcp/).



### DHCP Relay




DHCP Relay configuration in ACI is required when the DHCP server is not connected to the same subnet (broadcast domain) where the dynamic address distribution is required.

For ACI to function as a DHCP Relay agent, DHCP Option 82 must be supported by the DHCP server, with the following sub options:

- Agent Circuit ID
- Agent Remote ID
- VRF Name-VPN ID
- Server ID Override - needed only if DHCP server and client are in different VRF.
- Link Selection - needed only if DHCP server and client are in different VRF.

DHCP addresses can only be distributed on the primary subnet configured on the Bridge Domain. DHCP relay in ACI uses the primary SVI as Gateway IP Address (GIADDR) , which is in turn used to select the DHCP scope.

DHCP Relay can be configured as a Global Policy or as a Tenant Policy.

In the %%customerName initial deployment, DHCP Relay will be required. Refer to the Fabric Logical Design - Bridge Domains section for more details.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the DHCP Relay Policy needs to be defined in the input files:

<caption name="DHCP Relay Data Model">

```yaml
apic:
  tenants:
    - name: ABC
      policies:
        dhcp_relay_policies:
          - name: DHCP-RELAY1
            description: My Description
            providers:
              - ip: 6.6.6.6
                type: epg
                tenant: ABC
                application_profile: AP1
                endpoint_group: EPG1
```
</caption>

For further information on how the DHCP Relay Policy is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/infra_dhcp_relay_policy/).



### Monitoring Policies




A named monitoring policy can be defined, or the 'default' policy can be used.

Policies for Stats collection, Callhome, SNMP, Syslog, etc. are defined under Monitoring Policies. Administrators can create monitoring policies with the following four broad scopes:

- Fabric Wide: includes both fabric and access objects.
- Fabric: fabric ports, cards, chassis, fans, and so on.
- Access (also known as infrastructure): access ports, FEX, VM controllers, and so on.
- Tenant: EPGs, application profiles, services, and so on.

In the %%customerName design, the default monitoring policies are going to be used.



### Troubleshooting Policies







### SPAN







### SPAN Source Group




The SPAN source group contains a group of SPAN sources. A SPAN source is where network traffic is sampled. A SPAN source can be an endpoint group (EPG), one or more ports, or port traffic filtered by an EPG (access SPAN), a Layer 2 bridge domain, or a Layer 3 context (fabric SPAN). When you create a traffic monitoring session, you must select a SPAN source group and a SPAN destination. The type of session (tenant, access, or fabric) determines the allowed types of SPAN sources and destinations. The destination can be either a port or an EPG.

For SPAN source port, the port is not configured for any other purposes.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how SPAN Source Groups need to be defined in the input files:

<caption name="SPAN Source Group Data Model">

```yaml
apic:
  access_policies:
    span:
      source_groups:
        - name: INT1
          destination:
            name: TAP1
          sources:
            - name: SRC1
              direction: both
              access_paths:
                - node_id: 101
                  port: 1
```
</caption>

For further information on how SPAN Source Groups are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_span_source_group/).



### SPAN Destination Group




The SPAN destination group contains a group of SPAN destinations. A SPAN destination is where network traffic is sent for analysis by a network analyzer. A SPAN destination can be local or remote (ERSPAN). When you create a traffic monitoring session, you must select a SPAN source and a SPAN destination. The type of session (tenant, access, or fabric) determines the allowed types of SPAN sources and destinations. The destination can be either a port or an EPG. If the destination is a port, it is not one that has been configured for other purposes. For SPAN source port, the port is not configured for any other purposes.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how SPAN Destination Groups need to be defined in the input files:

<caption name="SPAN Destination Group Data Model">

```yaml
apic:
  access_policies:
    span:
      destination_groups:
        - name: TAP1
          description: My_SPAN_Destination
          node_id: 101
          port: 10
```
</caption>

For further information on how SPAN Destination Groups are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_span_destination_group/).

In the %%customerName design, no SPAN sessions, source, or destination groups will be defined at an initial stage.



## Switches



A Switch Profile can be seen as a container for switch selectors. Switch selectors are used to select node ID ranges and to associate them with a switch policy-group.

Switch Profiles are also used to associate node ID ranges with interface profiles to define the behavior of its respective switch ports, and, if required, with module profiles (used for configuring FEX modules). A switch profile could be the definition of a single switch, or it could be the definition of multiple switches that use the same policy and use the same interfaces.

Distinct Switch profiles are created for Leaf Switches and Spine Switches.


<caption name="Switch Profile Objects Relationship">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Switch_Profile_Objects_Relationship.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>




### Switch Policy Groups



Switch Policy Groups are templates for grouping the defined switch policies. A Switch Policy Group can be associated to the Leaf or Spine Switch Profile.

Spine Switch Policies for the fabric are summarized in table below.

<caption name="ACI-FABRIC-NAME - Switch Policy Group">

| Switch Policy Name | LLDP Policy | BFD ipv4 Policy | BFD ipv6 Policy |
| --- | --- |
</caption>

Leaf Switch Profiles are summarized in the table below.

<caption name="ACI-FABRIC-NAME - Switch Policy Group">

| Switch Policy Name | Forwardin Policy | BFD ipv4 Policy | BFD ipv6 Policy |
| --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Leaf Switch Policy Groups need to be defined in the input files:

<caption name="Leaf Switch Policy Group Data Model">

```yaml
apic:
  access_policies:
    leaf_switch_policy_groups:
      - name: ALL_LEAFS
        forwarding_scale_policy: HIGH-DUAL-STACK
        bfd_ipv4_policy: BFD-IPV4-POLICY
        bfd_ipv6_policy: BFD-IPV6-POLICY
```
</caption>

Below example of Spine Policy Group definition.

<caption name="Spine Switch Policy Group Data Model">

```yaml
apic:
  access_policies:
    spine_switch_policy_groups:
      - name: ALL_SPINES
        lldp_policy: LLDP-ENABLED
        bfd_ipv4_policy: BFD-IPV4-POLICY
        bfd_ipv6_policy: BFD-IPV6-POLICY
```
</caption>

For further information on how Leaf Switch Policy Groups are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_leaf_switch_policy_group/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.021">
An explicit Switch Policy Group will be configured and associated to all leaf and spine switches, even when all default policy profiles are used.
<br><br>
Rationale: Cisco recommends configuring explicit switch policy groups rather than relying on implicit defaults. This ensures that the intended policy set is clearly defined and traceable, prevents unexpected behaviour if defaults change after a software upgrade, and provides a single point of modification for future policy adjustments.
</tip>
<br><br>




### Leaf Switch Profiles



It was common practice to define one switch profile for each leaf switch and an additional switch profile for each vPC domain pair of leaf switches. However, it has been noticed in the field that this can easily lead into confusion that ends up in unenforced configuration standardization.

In the %%customerName ACI design, the 1 to 1 approach will be taken with both Interface Profiles and Switch Profiles: one Switch Profile will be defined for each Interface Profile, i.e., Switch Profiles will be created for all switches in a 1 to 1 relationship.

One Leaf Switch profile will be created per Leaf switch (regular, service, and Border leaf).


For the %%customerName ACI design, the Leaf Switch Profiles will use the following naming convention: [&#39;node-ID&#39;]

<caption name="ACI-FABRIC-NAME - Leaf Switch Profiles">

| Switch Profile | Node IDs | Pod |
| --- | --- | --- |
</caption>

The association of Leaf Switch Profile with Leaf Interface Profile for all the leaf nodes in the %%customerName ACI fabrics follows this sample:

<caption name="ACI-FABRIC-NAME - Sample Leaf Switch Profile with Interface Profile association">

| Switch Profile | Interface Profile |
| --- | --- |
</caption>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Leaf Switch Profiles need to be defined in the input files:

Auto-generated profiles.

<caption name="Leaf Switch Profiles Data Model - Auto-Generated">

```yaml
apic:
  auto_generate_switch_pod_profiles: true
  access_policies:
    leaf_switch_profile_name: "LEAF\\g<id>"
    leaf_switch_selector_name: "LEAF\\g<id>"
```
</caption>

Explicitly defined profiles.

<caption name="Leaf Switch Profiles Data Model - Explicitly Defined">

```yaml
apic:
  access_policies:
    leaf_switch_profiles:
      - name: LEAF1001
        selectors:
          - name: SEL1
            policy: ALL_LEAFS
            node_blocks:
              - name: BLOCK1
                from: 1001
        interface_profiles:
          - LEAF1001
```
</caption>

For further information on how Leaf Switch Profiles are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_leaf_switch_profile/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.022">
One Leaf Switch Profile will be created per leaf switch in a one-to-one relationship, each associated with a single corresponding Interface Profile.
<br><br>
Rationale: Cisco now recommends a one-to-one relationship between switch profiles and switches, replacing the older practice of creating separate profiles for individual switches and vPC pairs. This approach prevents configuration standardisation drift that has been observed in the field and simplifies both manual and automated provisioning.
</tip>
<br><br>




### Spine Switch Profiles



One Spine Switch Profile will be created per Spine switch. The Spine Switch Profile will use the following naming convention: [&#39;node-ID&#39;]

The spine switch profile will be associated with the corresponding spine interface profile.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Spine Switch Profiles need to be defined in the input files:

Auto-generated profiles.

<caption name="Spine Switch Profiles Data Model - Auto-Generated">

```yaml
apic:
  auto_generate_switch_pod_profiles: true
  access_policies:
    spine_switch_profile_name: "SPINE\\g<id>"
    spine_switch_selector_name: "SPINE\\g<id>"
```
</caption>

Explicitly defined profiles.

<caption name="Spine Switch Profiles Data Model - Explicitly Defined">

```yaml
apic:
  access_policies:
    spine_switch_profiles:
      - name: SPINE101
        selectors:
          - name: SEL1
            policy: ALL_SPINE
            node_blocks:
              - name: BLOCK1
                from: 101
        interface_profiles:
          - SPINE101
```
</caption>

For further information on how Spine Switch Profiles are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/access_policies/ap_spine_switch_profile/).




# Logical Design Updated
## Overview



This section is divided in two sub-sections:

- Building Blocks: The purpose of this sub-section is to briefly describe each one of the Tenant objects that are usually required in an ACI design as well as some important considerations that may not be easily found in the corresponding White Papers and official public documentation. This section should not describe in detail which objects will be defined in %%customerName's ACI design in particular.
- Tenant Architecture: The goal of this section is to describe the tenant objects that will be created for each one of the tenants defined in the %%customerName's ACI design. This section should explain the reasoning behind the creation of the corresponding tenant objects. It should describe them and reference the key decisions of the ACI design when possible. This section should describe %%customerName's whole tenant model, the segmentation approach, as well as the networking and application model.

This overview is intentionally kept concise so reviewers can focus on section-level design intent before implementation details. <ac:inline-comment-marker ac:ref="fresh-logical-comment">Key design elements include tenant isolation and role-based access control.</ac:inline-comment-marker>

<info name="Info">%%customerName logical design overview should be already described in chapter Design Overview.
</info>



## Building Blocks







### Tenants




A Tenant in ACI is a container that does not map directly to any legacy network constructs like VRFs, VLANs, Interfaces, etc. Instead, it is the highest-level container where these objects reside. Inside a Tenant, you can differentiate between the objects that define the tenant networking, such as VRF, Bridge Domains and Subnets, and the objects that define the tenant policies, such as Application Profiles, Endpoint Groups, and Contracts.

Tenants provide:

- Isolation: Tenants are isolated from one another, with the ability to share some resources.
- Role-Based Access Control: Tenants can be visible to only a set of users using the concept of Security Domains.
- Inheritance: Objects inside a Tenant inherit the top-level policies.

Three Tenants are deployed by default within ACI:

- infra: Used for leaf to leaf traffic within the Fabric, between PODs or Sites and for bootstrap protocols within the Fabric.
- mgmt: Used for management connectivity between the APIC and switch nodes, as well as for connectivity to other management systems (Syslog server, AAA servers, etc.)
- common: Used to create objects visible and shared to any other tenant.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Tenants need to be defined in the input files:

<caption name="Tenants Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      description: Tenant Prod
      security_domains:
        - SECURITY-DOMAIN1
```
</caption>

For further info on Tenants are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/tenant/).



### VRFs




- A Virtual Routing and Forwarding (VRF) object , also known as context in the ACI MIT, is very similar to VRFs in traditional environments. It is the Layer-3 forwarding domain within the fabric and defines the Layer-3 boundary for the traffic inside a Tenant. The exception to this are the VRFs defined in the common Tenant; these can can be used by all other Tenants.
- A VRF always needs to be assigned to a Tenant, and a Tenant can have more than one VRF.
- Some ACI objects, such as Bridge Domains and L3Outs must be associated to a VRF.

VRFs will use the following naming convention: [name]_VRF

VRFs have several configuration options that should be noted:

<caption name="Configuration Options for VRFs">

| Configuration Option | Values | Description |
| --- | --- | --- |
| IP Data Plane Learning | enabled/disabled | Controls whether IP addresses are learned in the data plane |
| Enforcement Direction | ingress/egress | Policy enforcement direction |
| Enforcement Preference | enforced/unenforced | Policy enforcement preference |
| Policy Control Enforcement Preference | enforced/unenforced | Contract enforcement preference |

</caption>

If vzAny is being used (more details about vzAny in the Contracts Chapter), the contract needs to be linked to the VRF as provider and/or consumer, according to the design specifications.

Finally, there are other policies that can be configured at a VRF level:

- End Point Retention Policy: Policy to configure the amount of time that Cisco ACI leaf switches hold entries before they timeout.
- Monitoring Policy: Policy to configure monitoring options for the objects in this Tenant.
- BGP Timers Policy: Defines BGP Protocol timers and configuration options (e.g., Keepalive intervals, Hold intervals, AS limit).
- BGP Address Family Context Policy: Defines eBGP and iBGP protocol distance and maximum ECMP.
- BGP Route-Target Profiles: Defines, per address-family, the route-target to be used (import, export).
- OSPF Timers Policy: Defines OSPF Protocol timers (OSPF hello and dead intervals)
- DNS Label Policy - Policy that configures parameters like DNS Server and Default Domain Name.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how VRFs need to be defined in the input files:

<caption name="VRFs Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      vrfs:
        - name: MAIN
          description: Main VRF
          bgp:
            timer_policy: BGP-TIMER1
          contracts:
            consumers:
              - PROD-CONT1
            providers:
              - PROD-CONT1
```
</caption>

- For further info on how VRFs are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/vrf/).
- For the complete list of VRFs that will be defined in this design in particular, please reference the corresponding YAML inventory files in: tenant-X.yaml



### BDs




A Bridge Domain (BD) is the abstract representation of a Layer 2 forwarding domain within the fabric, it is used to define a layer-two boundary within the fabric and is built with VXLAN overlays. A BD can be viewed as somewhat similar to regular VLANs in a traditional switching environment.

Bridge Domains will use the following naming convention: [name]_BD

BDs can be categorized into different types based on the use that they will have and the settings they are configured with. We can identify two main types of BDs:

- L2-only BD - This type of BD will provide only layer 2 connectivity between endpoints. An L2-only BD should have traditional L2 forwarding behavior (L2 unknown unicast flooding). This type of BD would be used for a VLAN whose default gateway (if any) is not configured in the ACI fabric, but rather in an external L3 device, such as a firewall or a load balancer. This type of BD would also be used during a migration from a legacy switching infrastructure, before all endpoints in the VLAN have been physically migrated from the legacy L2 infrastructure to an ACI leaf node and before the default gateway is migrated to ACI. Therefore, the EPG can be extended to external L2 switches.
- L3 BD - This type of BD will provide L3 connectivity between endpoints in different subnets. The default gateway of the subnet is the ACI fabric.

It is possible to further differentiate L3 BDs into sub-types, based on more detailed requirements of the corresponding network segments that they will give service to.

- L3 BD Variant A: An L3 BD with ACI forwarding behavior (hw-proxy) and ARP flooding disabled. This type of BD would be used for a VLAN whose default gateway is defined in the ACI fabric. No Active/Standby clusters of Firewalls or Load Balancers are expected to be in the network segment. If there was at any point a connection to a legacy L2 infrastructure, all endpoints in the VLAN should have been physically migrated from the legacy L2 infrastructure to an ACI leaf node. The EPG should not extend to any external L2 switch.
- L3 BD Variant B: An L3 BD with traditional L2 forwarding behavior (L2 unknown unicast flooding). This type of BD would be used for a VLAN whose default gateway is defined in the ACI fabric, but not all endpoints are physically connected to a leaf node; some endpoints may be connected to external L2 switches.

<caption name="Bridge Domains Configuration per Type">

| BD Type | L2 Unknown Unicast | Unicast Routing | ARP Flooding | Subnet | Comments |
| --- | --- | --- | --- | --- | --- |
| L2-only BD | Flood | Disabled | Enabled | No | Default gateway not in ACI\n EPG **extended** to external **L2 switch** |
| L3 BD Variant A | Flood | Enabled | Disabled | Yes | Default gateway in ACI\n EPG **not extended** to external **L2 switch** |
| L3 BD Variant B | Flood | Enabled | Enabled | Yes | Default gateway in ACI\nEPG **extended** to external **L2 switch** |
</caption>

L3 BDs need to have a subnet configured. The following parameters (among others) can be modified when creating a subnet:

- Private to VRF: Defines subnets under a BD to only be used in that VRF. The subnet will not be redistirbuted internally and will not be advertised to external L3 devices.
- Advertised Externally: Defines subnets to be advertised out of the fabric via L3Outs.
- Shared between VRF: Defines subnets under an endpoint group to be route leaked in order to have inter-VRF communication.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how BDs need to be defined in the input files:

<caption name="Bridge Domain Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      bridge_domains:
        - name: Web_BD
          vrf: MAIN
          unknown_unicast: proxy
          arp_flooding: false
          unicast_routing: true
          subnets:
            - ip: 10.0.0.1/24
              public: true
              private: false
              shared: false
```
</caption>

- For further info on how BDs are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/bridge_domain/).
- For the complete list of BDs that will be defined in this design in particular, please reference the corresponding YAML inventory files in: tenant-X.yaml

The following design decisions have been made in this section:

<tip name="Design Decision DD.023">
ARP flooding will be enabled on L3 Bridge Domains where Active/Standby firewall or load-balancer clusters are connected.
<br><br>
Rationale: Active/Standby clusters use gratuitous ARP to announce failover events. Without ARP flooding enabled, the standby device&#39;s ARP announcements may not reach all leaf nodes, causing traffic black-holing after a failover. Enabling ARP flooding in these specific BDs ensures that cluster failover is correctly propagated across the fabric.
</tip>
<br><br>




### APs




- The Application Profile is the construct that ties multiple EPGs together to represent an Application. An application profile contains as many EPGs as necessary that logically relate to the capabilities provided by an application.
- An Application Profile should be seen merely as a container of objects, such as EPGs and/or ESGs. It is important to point out that segmentation and policy is applied at the EPG or ESG level though, not at the Application Profile level.
- Similar to EPGs, Application Profiles play no role in networking; they can be used for organizational purposes.
- Application Profiles will use the following naming convention: [name]_AP
- The IaC data model for ACI regarding APs will be presented together with EPGs in the following chapter.



### EPGs




An EndPoint Group (EPG) is the most important object in the policy model of ACI. It is a collection of the devices that are connected to the network, directly or indirectly (endpoints). EPGs are completely decoupled from the physical and logical topology of the network. They are the tool that maps traffic from a leaf switch port to a bridge domain or security zone. One EPG will always belong to a single BD.

Endpoint Groups will use the following naming convention: [name]_EPG

EPGs contain endpoints that have common policy requirements such as security, virtual machine mobility (VMM), QoS, or Layer 4 to Layer 7 services. Policies apply to EPGs, never to individual endpoints.

You can assign 3 types os hosts to an EPG:

- Physical Hosts
- Virtual Hosts
- External Hosts

To assign physical hosts you can use static binding to map a specific leaf port and VLAN to an EPG, or even map an entire switch and VLAN to it. You can also configure the EPG mappings directly from the Attachable Access Entity Profile (AAEP). For virtual hosts, you can still use static binding or leverage VMM integration. This integration will allow the API to automate the mapping of specific EPGs to the virtual hosts using APIs from several virtualization solutions like VmWare, Nutanix, and more.

For external hosts, like external switches and routers, you can use L2Outs or L3Outs depending on the type of traffic. The latter has a specific chapter dedicated to it. L2Outs are very similar to normal static binding, where you extend the EPG to the ports connected to the external devices and map the corresponding VLANs of that EPG which will enable that L2 traffic to enter the ACI fabric.

By default, all endpoints that belong to the same EPG will be able to communicate between themselves and endpoints that belong to different EPGs will not. To enable inter-EPG traffic, you will need to use contracts, which has a separate chapter below. Instead, to disable default intra-EPG traffic, user needs to change the Intra EPG Isolation option to Enforced. This will then require to use contracts to enable connectivity between the endpoints of the same EPG.

Similar to BDs, EPGs can have subnets assigned to them, which can be seen as the default Gateway for devices belonging to that EPG. This option is normally only used in some specific situations for transit routing inter-VRF, which can be found in the ACI Whitepapers.

For more information regarding design considerations for EPGs, you can refer to the ACI White Paper Design Guide - EPG Considerations. The IaC data model for ACI formally defines the format of the data input files. This is an example of how EPGs need to be defined in the input files:

<caption name="Endpoint Group Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      application_profiles:
        - name: Application_1
          endpoint_groups:
            - name: Web_EPG
              bridge_domain: Web_BD
              preferred_group: false
              physical_domains:
                - PHY1
              vmware_vmm_domains:
                - name: VMM1
                  vlan: 135
                  primary_vlan: 100
                  secondary_vlan: 101
                  deployment_immediacy: lazy
                  resolution_immediacy: immediate
              static_ports:
                - node_id: 101
                  port: 10
                  mode: regular
              contracts:
                consumers:
                  - PROD-CONT1
                providers:
                  - PROD-CONT2
              subnets:
                - ip: 5.50.5.1/30
                  public: true
                  private: false
                  shared: true
              tags:
                - tag1
                - tag2
```
</caption>

- For further info on how EPGs are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/endpoint_group/).
- For the complete list of EPGs that will be defined in this design in particular, please reference the corresponding YAML inventory files in: tenant-X.yaml



### ESG




The Endpoint Security Group (ESG) is a component of Cisco's Application Centric Infrastructure (ACI) designed to enhance network security by grouping endpoints with similar security requirements. ESGs allow network administrators to apply consistent security policies across different types of endpoints; such as servers, virtual machines, and containers, ensuring a unified and simplified approach to network security management.

Endpoint Security Groups will use the following naming convention: [name]_ESG

The following are some of the key features of ESGs:

- Policy-Driven Security: ESGs enable administrators to define and enforce security policies based on the attributes of the endpoints rather than their physical or virtual locations. This abstraction simplifies the application of security measures and ensures that policies are consistently applied across the network.
- Micro-Segmentation: ESGs support micro-segmentation, which involves dividing the network into smaller, isolated segments. This segmentation reduces the attack surface and limits the spread of threats within the network. Each ESG can have specific security policies that control traffic flow between endpoints within the group and between different ESGs.
- Dynamic Membership: Endpoints can be dynamically assigned to ESGs based on their attributes, such as IP address, MAC address, VM name, or other metadata. This dynamic assignment ensures that security policies automatically adapt to changes in the network environment, such as the addition or removal of endpoints.

These features translate into the following benefits for users applying ESGs to their fabrics:

- Enhanced Security: ESGs provide a robust framework for implementing consistent and granular security policies across the network, reducing the risk of security breaches and ensuring that all endpoints are adequately protected.
- Simplified Management: By abstracting security policies from the physical network topology and focusing on endpoint attributes, ESGs simplify the management of security policies. Administrators can easily apply, update, and monitor security measures without needing to reconfigure the network.
- Flexibility and Scalability: ESGs support dynamic membership and policy-driven security, making it easy to scale and adapt to changes in the network. As new endpoints are added or existing ones are reconfigured, they can automatically inherit the appropriate security policies.
- Improved Compliance: ESGs help organizations comply with regulatory requirements by ensuring that security policies are consistently enforced across all endpoints. This consistent enforcement aids in auditing and reporting, demonstrating compliance with industry standards and regulations.

The process of deploying ESGs in ACI can be summarized as follows:

- Define ESGs: Identify and define ESGs based on the security requirements of different types of endpoints within the network. For example; create separate ESGs for web servers, database servers, and employee workstations.
- Assign Endpoints: Use attributes like IP addresses, MAC addresses, or application profiles to assign endpoints to the appropriate ESGs. This can be done manually or automatically using ACI dynamic membership capabilities.
- Create Security Policies: Define security policies for each ESG, specifying rules for traffic flow, access control, and threat prevention. Policies can be as granular as needed to meet the security requirements of each group.
- Apply and Monitor: Apply the defined security policies across the network. Use ACI monitoring and analytics tools to continuously monitor traffic, detect anomalies, and ensure compliance with security policies.

For more information regarding design considerations for ESGs, please refer to the Cisco ACI Endpoint Security Group (ESG) Design Guide. The IaC data model for ACI formally defines the format of the data input files. This is an example of how ESGs need to be defined in the input files:

<caption name="Endpoint Security Group Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      application_profiles:
        - name: Application_1
          endpoint_security_groups:
            - name: Web_ESG
              description: IP Subnet Selector 1
              vrf: MAIN
              shutdown: true
              intra_esg_isolation: true
              preferred_group: true
              contracts:
                consumers:
                  - PROD-CONT3
                providers:
                  - PROD-CONT4
              masters:
                - application_profile: Application_1
                  endpoint_security_group: Servers_ESG
              tag_selectors:
                - key: KEY1
                  operator: contains
                  value: VALUE1
              epg_selectors:
                - application_profile: Application_1
                  endpoint_group: Web_EPG
              ip_subnet_selectors:
                - value: 10.1.1.0/24
```
</caption>

- For further info on how ESGs are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/endpoint_security_group/).
- For the complete list of ESGs that will be defined in this design in particular, please reference the corresponding YAML inventory files in: tenant-X.yaml



### Contracts




Contracts are the fundamental way security is enforced in an ACI fabric. The ACI solution follows an allow-list model, meaning permitted traffic needs to be explicitly defined. Contracts are constructs that are applied to the EPGs of the fabric and define this inter-EPG communication. If there are no contracts applied, by default the only communication permitted is between endpoints in the same EPG. It is important to note that contracts are only applied to unicast traffic. Any BUM traffic is implicitly permitted.

Contracts will use the following naming convention: [name]_CT

Contracts follow a consumer-provider model. An EPG provides a contract that is consumed by another EPG, thus allowing communication. An EPG can consume and/or provide several contracts and a contract can be used multiple times. For example; one EPG can provide a contract that is consumed by three other EPGs. In this case, the provider EPG can communicate to any of the three consumers and vice-versa, but the consumers cannot communicate between themselves. Defining which EPG is the consumer or provider for a contract allows to establish the direction of said contract and where to apply the Access Control List filtering, showed at figure below.


<caption name="Contracts">

![image](/api/v1/projects/df55fc75-d510-4f14-b791-381a93756c73/images/Contracts.png?tech_path=docascode%2Ftech-aci-v1.0.2&branch=main)
</caption>


Contracts have an associated scope that defines the constraints of operation and between which endpoints can the contract be applied. The options are:

- VRF: This is the default option. This contract will only be applicable between EPGs that belong to the same VRF.
- Application: This option only allows the contract to be applied between EPGs in the same Application Profile.
- Tenant: Similar to Application scope, but for all EPGs inside the same Tenant. This options allows EPGs in different VRFs to communicate between each other.
- Global: This contract can be applied between any EPGs across any Tenants in the ACI Fabric.



### Subjects




A contract will always have at least one subject. This object is a construct that references one or more filters. Usually, subjects group similar filters together for better management. As an example, a "remote-access" subject can be created with filters that permit or deny the telnet and SSH traffic. Subjects have the following main options:

- Apply Both Directions: This option is true by default. It states that when a filter is created inside this subject, the filter is applied on both consumer-to-provider and provider-to-consumer directions. If set to false, then the filters inside this subject will need to be applied in a specific direction.
- Reverse Filter Ports: This option can only be enabled when "Apply Both Directions" is set to true. When enabled , a created filter inside this subject will switch the source and destination ports based on the direction of the traffic being filtered. As a concrete example, if a filter is created that matches traffic with source port 22 on the consumer-to-provider direction, ACI will automatically apply the same filter with destination port 22 on the provider-to-consumer direction.
- L4-L7 Service Graph and Policy Based Redirect (PBR): PBR has a specific section, where further details are explained. However, they are applied to contract subjects.



### Filters




A filter is an entry for some specific traffic to be matched on, based on specific fields like source and destination ports and IP protocol. Traffic that matches the filter can either be permitted or denied, based on the action chosen. Traffic hitting the filter can also be logged.

Filters will use the following naming convention: [name]_FLT



### vzAny and Preferred Group




Because of the complexities associated with explicitly defining allowed traffic and also due to the scalability issues inherent with this approach, some options were devised to simplify this process, specially for use cases where most of the traffic is to be allowed inside a given VRF or between a subset of the EPGs.

vzAny represents all the EPGs inside of a VRF. If a contract is applied to vzAny, its rules are applied to all the EPGs inside the VRF. vzAny can be the provider, consumer, or provider and consumer of a given contract. When vzAny is the provider and consumer of the same contract, intra-VRF traffic that matches the defined filters is allowed.

Preferred Group is a feature that allows EPGs in the same VRF that belong to the group to communicate without the need of any contracts between themselves. One VRF can only have one Preferred Group which means that an EPG can either belong or not belong to the Preferred Group. For communications between a member of the Preferred Group and a non-member, a contract is still necessary, no matter who is the consumer or provider.

For more information regarding design considerations for Contracts, you can refer to the Cisco ACI Contract Guide White Paper.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how Contracts and Filters need to be defined in the input files:

<caption name="vzAny and Preferred Group Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      contracts:
        - name: PROD-CONT1
          scope: context
          subjects:
            - name: PROD-SUBJ1
              service_graph: PROD_SGT
              filters:
                - filter: PROD-FLT1
                  action: permit
      filters:
        - name: PROD-FLT1
          entries:
            - name: HTTP
              ethertype: ip
              protocol: tcp
              source_from_port: 80
              source_to_port: 80
```
</caption>

For further info on how Contracts are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/contract/). For Filters, refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/filter/).



### Security Enforcement




By default, there is free communication among end points inside an EPG. Contracts are enforced between two EPGs, a consumer EPG, an a provider EPG.

This paragraph describes additional configuration possibilities offered by ACI, to cover different requirements.



### Intra EPG Isolation




There are certain use cases where no communication among end points is desired. For example, when backup clients are placed in an isolated VLAN so they can only communicate with a Backup server, but not among each other.

By enforcing Intra EPG isolation in the EPG configuration, we obtain that all end points in the EPG cannot communicate with each other. They can only communicate with another EPG, provided a contract is applied.



### Intra-EPG Contract




A contract can be applied to the EPG as "Intra EPG". This means that the applied contract is enforced among all the End Points in that EPG.

For more information regarding design considerations for micro segmentation, you can refer to the Cisco ACI Contract Guide White Paper.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how uSeg Endpoint Group need to be defined in the input files:

<caption name="Intra-EPG Contract Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      application_profiles:
        - name: AP1
          useg_endpoint_groups:
            - name: uSeg_EPG1
              bridge_domain: PROD_BD1
              physical_domains:
                - PHY_DOM
              static_leafs:
                - node_id: 202
              contracts:
                consumers:
                  - PROD-CON1
                intra_epgs:
                  - INTRA-CON1
              masters:
                - application_profile: AP1
                  endpoint_group: EPG1
              useg_attributes:
                ip_statements:
                  - name: ip_1
                    use_epg_subnet: false
                    ip: 10.10.10.120/25
                mac_statements:
                  - name: mac_1
                    mac: 00:11:22:aa:bb:cc
```
</caption>

For further info on how uSeg Endpoint Group are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/contract/).



### L3Outs




A Layer-3 external network (also known as a Layer-3 Outside or Routed Outside) is required whenever an external environment is accessible via routed links. The Fabric Leaf Switches are able to peer with external networks and redistribute the routing information throughout the Fabric. Supported Routing Protocols are OSPF, BGP, and EIGRP. Static Routing is also supported.

L3OUTs will use the following naming convention: [name]_L3OUT

Border leaf switches are the ACI switches connected with external L3 devices. Routed interfaces, sub-interfaces, and SVI can be used for this connectivity.

The Fabric uses the BGP protocol internally to distribute external routing information through the domain to each of the leaf switches that require the information. Redistribution of the external routes into the fabric BGP occurs at the border leaf switches. Route reflectors are used at the spine layer to reduce the need for full mesh BGP connectivity inside the fabric. It is possible to statically define which nodes should act as BGP route reflectors within the fabric using a pod policy.

Note that external routes are advertised to a leaf switch only when they have 'interest' in a particular tenant. For example, if a leaf switch has end points connected only in the VRF1 context, external routes associated with the VRF2 context will not be distributed to that leaf.

- For routing to destinations outside of the fabric, several options are supported:
  - Static Routes
  - OSPFv2 (IPv4)
  - OSPFv3 (IPv6)
  - iBGP
  - eBGP (IPv4 and IPv6)
  - EIGRP (IPv4 and IPv6)
- If static routes are used, the destination and next hop are specified in the L3Out Node Profile.
- A Layer 3 external outside network (l3extOut object) includes the routing protocol options (BGP, OSPF, or EIGRP or supported combinations) and the switch-specific and interface-specific configurations.
- Note the L3out has a relation with the VRF. For every VRF one or more L3out can be defined.
- The L3out Node Profile, contains the switch specific information (router_id, static routes).
- The L3out Interface Profile contains the interface specific information and the attachment to the external L3 device (interface type, IP addresses, routing protocol specific interface policies).
- The external prefixes are represented by the L3 External EPG. Routed connectivity to external networks is enabled by associating a fabric access (infraInfra) external routed domain (l3extDomP) with the Layer 3 external instance profile (l3extInstP or external EPG), which is representing an external subnet.The subnet 0.0.0.0/0 in the external EPG is a catch-all and represents all prefixes.
- The External EPG object (l3extInstP) EPG exposes the external network to the tenant EPGs through application of a contract.
- In IaC data model, L3out Node and Interface Profiles can either be auto-generated, one per L3out, or can be defined explicitly.
- For more information regarding design considerations for L3out, you can refer to the Cisco ACI L3out White Paper.
- The IaC data model for ACI formally defines the format of the data input files. This is an example of how L3out with eBGP neighbor need to be defined in the input files:

<caption name="L3Outs Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      l3outs:
        - name: L3OUT-VRF1-PROD
          vrf: VRF1-PROD
          domain: L3OUT-EXTDOM
          node_profiles:
            - name: LEAF-101
              nodes:
                - node_id: 101
                  router_id: 1.1.1.1
                  static_routes:
                    - prefix: 192.168.1.0/24
                      description: eBGP-Loopback-subnet
                      next_hops:
                        - ip: 172.16.1.4/29
          interface_profiles:
            - name: LEAF-101
              interfaces:
                - channel: VPC1
                  svi: true
                  scope: local
                  vlan: 301
                  ip_a: 172.16.1.2/29
                  ip_b: 172.16.1.3/29
                  ip_shared: 172.16.1.1/29
                  bgp_peers:
                    - ip: 192.168.1.1
                      remote_as: 65010
                      ttl: 4
                      local_as: 65150
          external_endpoint_groups:
            - name: EXTEPG-VRF1
              subnets:
                - prefix: 0.0.0.0/0
              contracts:
                providers:
                  - PROD-CON1
```
</caption>

For further info on how L3out are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/l3out/).



### PBR




Policy Based Redirection (PBR) is an ACI feature that allows the redirection of traffic between security zones to L4-L7 devices, such as Firewalls, Intrusion Prevention Systems, and Load Balancers. With it, there is no need for these devices to be the default gateway for the endpoints, nor configuring VRF sandwiching or VLAN stitching. Traffic to be redirected can be selectively chosen based on a number of attributes, like protocol or port. PBR requires a service graph attached to the contract between endpoint groups (EPGs). A service graph will have one or more L4-L7 devices, called Service Nodes, chained together to describe through which appliances should the traffic flow.

We can divide PBR into two types:

- L3 PBR - This is the most common form of PBR, where L3 Service Nodes are used and traffic is routed to them. The service graph devices will have an IP address.
- L1/L2 PBR - In this case, the devices are in L1 or L2 mode (inline IPS or transparent firewall, for example). Traffic is bridged to the Service Nodes

Furthermore, we can decide to connect the service graph nodes to the ACI fabric in two different modes:

- One-arm mode - In this mode, the ingress and egress interface of the device is exactly the same. This can be used for east-west traffic where only the inside interface is to be used, or for an "all EPGs to all EPGs" use case, as well as intra-EPG contracts.
- Two-arm mode - In this mode, the ingress and egress interfaces of the device are logically different, for example with a different sub-interface or different encapsulation VLAN. For L1/L2 PBR this mode is a requirement. It is also commonly used for north-south traffic, separating an inside interface and an outside interface.

Finally, PBR can be applied according to the direction of the traffic in two different ways:

- Bidirectional PBR: This is the most common form of PBR, where traffic is redirected to the Service Node in both directions, either from consumer EPG to provider EPG or vice-versa. For example, when a Firewall is inserted in between two EPGs and the design requires the traffic to be inspected regardless of the direction.
- Unidirectional PBR: This form of PBR is mainly used when traffic should only be redirected in one direction. A common example is Load Balancer integration without Source Network Address Translation (SNAT). In this case, traffic to the Load Balancer's virtual IP address is routed by the fabric, without the need for PBR, before being replaced with the correct destination IP. Since the Load Balancer does not replace the source IP, traffic in the opposite direction needs PBR to be redirected to the Service Node.

<info name="Info">For more details about these configuration options, check the ACI PBR Service Graph Design White Paper.</info>

For a successful PBR configuration, you need the following constructs:

- PBR nodes Bridge Domain or L3Out
- L4-L7 Devices
- Service Graph Template
- Device Selection Policy
- Contract to which to apply the Service Graph

The IaC data model for ACI formally defines the format of the data input files. This is an example of how PBR needs to be defined in the input files:

<caption name="PBR Data Model">

```yaml
apic:
  tenants:
    - name: PROD
      services:
        redirect_policies:
          - name: PROD-PBR1
            l3_destinations:
              - ip: 1.1.1.1
                mac: 00:00:00:11:22:33
        l4l7_devices:
          - name: FW-1
            physical_domain: PHY1
            concrete_devices:
              - name: FW-1
                interfaces:
                  - name: FW-INT1
                    node_id: 101
                    port: 11
            logical_interfaces:
              - name: FW-INT1
                vlan: 135
                concrete_interfaces:
                  - device: FW-1
                    interface_name: FW-INT1
        service_graph_templates:
          - name: PROD_SGT
            redirect: true
            device:
              name: PBR-BD1
        device_selection_policies:
          - contract: PROD-CONT1
            service_graph_template: PROD-SGT
            consumer:
              redirect_policy:
                logical_interface: FW-INT1
                bridge_domain:
            provider:
```
</caption>

For further info on how PBRs are defined in the IaC Data Model for ACI, please refer to these links:

- Redirect Policy
- L4-L7 device
- Service Graph Template
- Device Selection Policy

For the complete list of Service Graphs with PBR that will be defined in this design in particular, please reference the corresponding YAML inventory files in: tenant-X.yaml



## Tenant Common Architecture



The common tenant will be used for shared services, such as backup services for endpoints located at other tenants.

No objects will be defined in the common tenant for use in other tenants, such as VRFs, contracts, etc. Those objects will be defined in the corresponding user-defined tenants.



## Tenant Architecture



To be filled with content



### VRFs



Only one VRF will be created in the PROD tenant. All BDs and L3Outs will be associated to this VRF.

There is no need to create an additional VRF in this tenant because the all communication among EPGs in this tenant will be determined by contracts, either with or without redirection to an E-W FW.

The following VRFs will be defined in the PROD tenant:


<caption name="Tenant VRF">

| Tenant | VRF |
| --- | --- |
| PROD | PROD |

</caption>

The PROD VRF will be configured with these settings:

<caption name="PROD VRF settings">

| Property | VRF |
| --- | --- |
| Policy Control Enforcement | Enforced |
| Policy Control Enforcement Direction | Ingress |
| Preferred Group | Disabled |

</caption>



### BDs



This tenant will contain both L3 BDs and L2-only BDs.

The next table shows the settings for both types of BDs:

<caption name="BD settings per type in tenant">

| BD Type | L2 Unknown Unicast | Unicast Routing | ARP Flooding | Subnet | Comments |
| --- | --- | --- | --- | --- | --- |
| L2-only BD | Flood | Disabled | Enabled | No | Def GW is not ACI EPG extended to external L2 switches |
| L3 BD Variant A | Hardware Proxy | Enabled | Disabled | Yes | Def GW is ACI EPG not extended to external L2 switches |
| L3 BD Variant B | Flood | Enabled | Enabled | Yes | Def GW is ACI EPG extended to external L2 switches |

</caption>



### APs



The following Application Profiles will be defined in the PROD tenant:

<caption name="Application Profiles - tenant">

| AP Name | Alias | Description |
| --- | --- | --- |
| PROD1_AP |  | AP for all Production/Phase 1 EPGs |

</caption>



### Segmentation



For this deployment, an application-centric approach will be followed. The Endpoints will be segmented by role.

- App
- Web
- Database

**EPGs**

**Preferred Group**

**Contracts**

**vzAny**

**ESGs**



### L3Outs



To be filled with content



### PBR



To be filled with content



## Tenant N



To be filled with content




# ACI Hardening







## Overview



Cisco ACI is a security hardened platform out of the box and compliant with various industry standards and certifications, such as:

- Common Criteria (Cisco ACI Certification Report)
- FIPS 140-2 (Cisco ACI Compliance Letter)
- DpD UC APL (Cisco ACI Certification Letter)

During the Cisco ACI fabric bring-up, or whenever a new device is added into the fabric, an authentication process will be triggered, in which every node will be authenticated by the APIC controllers using X.509 certificates which are unique and digitally signed at manufacturing time.

These certificates are securely stored in a secure hardware crypto-module knows as Trusted Platform Module (TPM) on APIC side and Trusted Anchor Module (TAM) on Nexus 9000. All messaging within the fabric used for configuration, monitoring, and operations are encrypted.

Depending on the hardening requirements of the %%customerName's organization, further tuning of the security settings can be required. The following chapter provides recommendations for hardening ACI in the %%customerName's setup, based on the three known areas:

- Management Plane
- Control Plane
- Data Plane

This may result in duplication with other chapters, for example the System Settings section. However, the aspects of the %%customerName ACI design listed here are shown again in a summarized form to provide an overview of security and hardening related topics across the whole environment.

<info name="Info">This chapter is based on the Cisco white paper Cisco ACI Hardening and the APIC Security Configuration Guide (different releases) and summarizes the most important aspects for this design document. For further information, please review these documents in detail. This content is based on ACI version 6.0.
</info>



## Building Blocks







### Securing the Management Plane







### AAA




The implementation of the Principle of Least Privilege is one of the key aspects to harden the ACI environment. ACI offers a very strong Role-based Access Control (RBAC) feature set.

Cisco ACI supports user authentication with local and remote identity providers. During normal operation, a centralized identity platform should be used. Local user accounts must be used for limited use cases only, e.g., as fallback if the remote systems are not available. With AAA Fallback ACI provides a feature to enable local accounts only if remote authentication providers become unavailable (using ICMP Ping Check or Server Monitoring).

The following design decisions have been made in this section:

<tip name="Design Decision DD.024">
A centralized identity platform will be used.
<br><br>
Rationale: Centralized identity platforms provide a single point of control and management, reducing the attack surface and improving auditability.
</tip>
<br><br>




### Remote Authentication Providers




The following remote authentication providers are supported:

- TACACS+
- RADIUS
- LDAP
- RSA SecurID
- SAML (using either ADFS, Okta SSO or PingFederate)
- DUO (from Cisco APIC release 5.0(1) using DUO Proxy RADIUS server or DUO Proxy LDAP Server)
- OAuth2.0 (from Cisco APIC release 5.2(3) using Authorization Code grant type)

The IaC data model for ACI formally defines the format of the data input files. This is an example of how a TACACS Provider need to be defined in the input files:

<caption name="Tacacs Providers Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      tacacs_providers:
        - hostname_ip: 1.1.1.1
          key: '123'
```
</caption>

- For further info on how the TACACS Provider are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/tacacs/).
- For further info on how the RADIUS Provider are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/radius/).
- For further info on how the LDAP are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/ldap/).



### Local Users




The following guidelines are applied when using local users:

- Configure a reduced number of personal local accounts for specific use cases. Avoid using generic accounts, as this makes accounting and account revoking more challenging.
- Configure AAA Fallback Check to ensure local accounts are only used when remote authentication providers are not available.
- Harden these local accounts properly, using the recommendations explained in coming sections: Password Strength Check and Dual-Factor Authentication.

Cisco ACI uses a crypt library with a SHA256 one-way hash for storing passwords. At rest hashed passwords are stored in an encrypted filesystem. The key for the encrypted filesystem is protected using the Trusted Platform Module (TPM).

<info name="Info">Note that the admin account in Cisco APIC is not equivalent to the root account and cannot be deleted: while the admin account has complete permissions to manage Cisco ACI fabric configuration, it does not have access to the underlaying software components and filesystem that Cisco ACI devices use to run.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how a local user need to be defined in the input files:

<caption name="Local Users Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      users:
        - username: user_1
          password: password_1
          domains:
            - name: all
              roles:
                - name: admin
                  privilege_type: write
            - name: common
```
</caption>

For further info on how the local user are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/user/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.025">
A minimal number of personal local accounts will be created, generic shared accounts will be avoided, and AAA Fallback Check will be enabled to restrict local account usage to remote-authentication-unavailable scenarios.
<br><br>
Rationale: Reducing local accounts and avoiding generic credentials limits the attack surface and improves auditability. AAA Fallback Check ensures local accounts are only used as a last resort when remote authentication providers are unreachable, maintaining centralised access control under normal conditions.
</tip>
<br><br>




### AAA Fallback




To allow access to the APICs or switches when remote authentication provider becomes unreachable, AAA Fallback can be used. There is a hidden login domain named "fallback" that allows using the local user database in case of lockout.

To check if the remote authentication provider is available or not can be done using the ICMP Ping Check (simple ICMP echo) or Server Monitoring (periodic authentication checks).

<info name="Info">Fallback is not an available option in the Login Domain dropdown. To login into the Cisco APIC using Fallback, the following syntax must be used:
CLI: apic#fallback\\<local_username>
GUI: apic:fallback\\<local_username></info>

The following table provides an overview of supported remote authentication providers to be configured with AAA Fallback.

<caption name="ACI-FABRIC-NAME - AAA Fallback Support">

| Authentication Providers | AAA Fallback Support |
| --- | --- |
| N/A | disabled |

</caption>

1 Remote authentication providers will always be reported as unavailable where AAA Fallback is not supported. Hence, Fallback will always be possible.

The following design decisions have been made in this section:

<tip name="Design Decision DD.026">
AAA Fallback will be enabled so that local authentication is available when remote authentication providers (e.g. TACACS+) become unreachable.
<br><br>
Rationale: Without AAA Fallback, a remote-authentication outage could lock administrators out of the fabric entirely. Enabling fallback ensures a last-resort access path through local accounts, preserving the ability to troubleshoot and restore services during authentication infrastructure failures.
</tip>
<br><br>




### Password Strength




A password strength check is enabled by default and the following criteria must be matched:

- Must contain between 8 and 80 characters.
- Must contain at least three of the following:
- Lower Case Letters
- Upper Case Letters
- Digits Special Characters (excluded $, ? and =)
- Must not contain characters repeated more than three consecutive times.
- Must pass a password dictionary check (English dictionary).
- Must not be identical to username (or reversed username).
- Must not be blank.

If required by %%customerName, a customized Password Strength Profile can be created to adopt e.g., the minimum password length.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how AAA settings need to be defined in the input files:

<caption name="Password Strength Data Model">

```yaml
apic:
  fabric_policies:
    aaa:
      remote_user_login_policy: no-login
      default_fallback_check: true
      default_realm: local
      console_realm: tacacs
      console_login_domain: tacacs
      security_domains:
        - name: SEC1
          restricted_rbac_domain: true
      management_settings:
        password_strength_check: true
        web_token_timeout: 600
        web_token_max_validity: 24
        web_session_idle_timeout: 1200
```
</caption>

For further info on how the AAA settings are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/aaa/).



### Dual-Factor Authentication




ACI supports 2FA using One-Time Password (OTP). This can be configured on a per-user level and should be enabled for all local users. However, 2FA is not enabled for the admin user to ensure that the Cisco ACI Fabric can be accessed with last resort credentials in case any other method fails.

The following design decisions have been made in this section:

<tip name="Design Decision DD.027">
Two-factor authentication (OTP) will be enabled for all local user accounts except the admin account.
<br><br>
Rationale: Enabling 2FA strengthens access security by requiring a second factor beyond the password. The admin account is excluded to preserve a last-resort access path in scenarios where the OTP infrastructure is unavailable, ensuring administrators can still recover the fabric.
</tip>
<br><br>




### User Authorization




Cisco ACI uses a RBAC model based on three main elements:

- Privileges: enables permissions to read and/or write objects from a given class (listed in the Object Model configuration).
- Roles: privileges can be grouped together into a Role, which can be then associated to a user to allow that user to manage a certain set of classes.
- Security Domains: represents a section of the Management Information Tree (MIT), for example, a tenant or a set of switches.

Administrators can configure granular permissions and effectively implement the Principle of Least Privilege by combining these concepts of Security Domain, Roles, and Privileges. To review the pre-defined roles and their privileges please follow this link: AAA RBAC Roles and Privileges. If necessary, custom roles can be defined as well.

For remote authentication Cisco ACI supports the methods described below to configure permission to each user.

- Cisco AV Pairs: attribute-value pairs are used to define specific authentication, authorization, and accounting elements in a user profile.
- Group Mapping: user privileges are assigned based on the group the users belong to, which is received from the remote authentication provider encoded in a given attribute, such as LDAP "memberOf"

The table below provides an overview of supported combinations.

<caption name="ACI-FABRIC-NAME - Supported mechanisms to receive user privileges from remote authentication providers">

| Provider | Cisco AV Pairs | Group Mapping |
| --- | --- | --- |

</caption>




### Accounting and Audit Logs




Cisco ACI records all login sessions as well as configuration changes. For login sessions, the following information is stored:

- Username
- IP address initiating the session
- Type (HTTPS, REST, etc.)
- Session time and length
- Token refresh

For configuration changes (create, update, or delete), the following information is stored:

- Time stamp
- User
- Action (creation, deletion, modification)
- Affected object
- Description

The logs can be accessed via GUI, CLI and, REST API.

Monitoring Policies are used to customize Cisco ACI monitoring configuration, including the export of logs. Following mechanisms are supported:

- Call home
- Syslog (over UDP, TCP, TLS)
- TACACS+

<info name="Info">Cisco ACI does not export any audit logs or session logs via these mechanisms by default. Therefore, operators need to, as a minimum, modify these default Monitoring Policies to start exporting audit and session logs.</info>

The following design decisions have been made in this section:

<tip name="Design Decision DD.028">
Accounting and audit logs will be exported to an external server.
<br><br>
Rationale: Cisco recommends that in case an APIC is lost, or its hard drives are damaged, some audit logs may be lost forever. Exporting the logs to an external server ensures that they are available even in such scenarios.
</tip>
<br><br>




### Restricting Management Access




Cisco ACI contracts can be configured under the management tenant to restrict which traffic flows are allowed to reach the management interfaces of Cisco ACI, including both out-of-band and in-band.

Out-of-Band Management Contracts (stateful using iptables):

- Provided by Out-of-Band EPG (including all switch and APIC management interfaces)
- Consumed by External Management Network Instance Profiles (external entities that are allowed to communicate to the fabric)
- Applied only in one direction, only inbound traffic can be restricted

In-Band EPG Management Contracts (stateless using zoning rules):

- Provided/consumed by In-Band EPG (including all switch and APIC in-band management interfaces)
- Provided/consumed by EPG or External EPG within the management tenant
- Can and must be applied in both directions to allow outbound traffic

<info name="Info">Granular management contracts should be used to restrict not only the ports being used, but also the sources that are allowed to reach the fabric on those ports, ensuring that only the protocols that are needed are allowed.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how a OOB contract needs to be defined in the input files:

<caption name="Restricting Management Access using Contracts Data Model">

```yaml
apic:
  tenants:
    - name: mgmt
      oob_contracts:
        - name: OOB-CON1
          subjects:
            - name: OOB-SUB
              filters:
                - filter: ALL
```
</caption>

For further info on how the OOB contract are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/tenants/oob_contract/).



### Disable Insecure Protocols and Ciphers




Secure protocols with strong encryption should always be preferred. This of course applies to HTTPS over HTTP, SSH over Telnet, SFT/SCP over FTP. In Cisco ACI HTTP and Telnet is disabled by default.

In addition, Cisco ACI offers the option of configuring the ciphers used. Depending on the requirements of the %%customerName's organization, these should be adjusted accordingly and obsolete procedures are disabled. For example, TLS1.0/1.1.

The following design decisions have been made in this section:

<tip name="Design Decision DD.029">
Insecure protocols (HTTP, Telnet, FTP) will remain disabled, HTTPS/SSH/SCP will be used exclusively, and obsolete TLS versions (1.0/1.1) will be disabled.
<br><br>
Rationale: HTTP, Telnet, and FTP transmit credentials and data in clear text, exposing the management plane to eavesdropping and man-in-the-middle attacks. ACI disables these by default; keeping them disabled and enforcing modern TLS versions aligns with industry security best practices and reduces the attack surface.
</tip>
<br><br>




### FIPS Mode




FIPS mode can be enabled to limit the use to FIPS 140-2 compliant crypto libraries (Certificate #4036) in ACI. The FIPS Object Module is supported for the following protocols:

- TLS v1.2 and v1.3
- SSHv2
- SNMPv3

<warning name="Warning">Before enabling FIPS mode, non-supported versions of the protocols listed above should be disabled before enabling FIPS mode. Enabling FIPS mode requires a system-wide reboot to take effect. For more information guidelines and limitations for FIPS, see the Cisco APIC Security Configuration Guide.</warning>



### REST API Hardening







### REST API Authentication Methods




Two methods can be used in Cisco ACI to authenticate against the REST API:

- Username/Password: login via POST request (must be send via HTTPS to be encrypted)
- Signature-based: utilizes X.509 certificates for every transaction

<info name="Info">X.509 certificates can only be configured for local users. Remote users are not supported with signature-based authentication.</info>



### REST API DoS Protection




The REST API can be protected against DoS attacks by HTTP/HTTPS throttling for AAA logins or HTTP/HTTPS global throttling.

HTTP/HTTPS throttling for AAA login:

- Pre-configured by default for aaaLogin and aaaRefresh
- Two-stage rate limiter is configured on NGINX
- Maximum of 2 request per second, with a maximum burst of 4
- Can be configured if required

HTTP/HTTPS global throttling:

- is disabled by default, can be enabled in Management Access Policy
- applicable to any API endpoint

When evaluating a possible value for this rate limit, consider the following things:

- A maximum burst of 2x the rate limit is automatically configured
- Rate limit is applied independently on a per-client-IP-address basis. Hence, if one client is exceeding the allowed rate and being throttled, this does not affect other clients with a different IP address.
- Request coming from the APIC itself (GUI/CLI) are not subject to the rate limit.



### Further Best Practices







### Display Login Banners




Login banners can be displayed to inform malicious users that they are not permitted to use the system. The content of login banners should be discussed with a legal counsel. From a security point of view, a login banner should not contain any specific information about the router name, model, software, or ownership.

The IaC data model for ACI formally defines the format of the data input files. This is an example of how a Login Banner needs to be defined in the input files:

<caption name="Display Login Banners Data Model">

```yaml
apic:
  fabric_policies:
    banners:
      apic_gui_alias: APIC GUI BANNER
      apic_gui_banner_url: APIC GUI BANNER URL
      apic_cli_banner: APIC CLI BANNER
      switch_cli_banner: SWITCH CLI BANNER
```
</caption>

For further info on how the GUI and CLI Banner are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/banner/).



### Console Access




Many organizations define requirements for access to infrastructure in failure scenarios, i.e., when central services, e.g., TACACS, are not available. The console port provides a last-resort to access devices. Therefore, local authentication should be used by default. As mentioned, local accounts must be hardened by using strong passwords and dual-factor authentication.

Operational teams should also document and periodically test break-glass console access procedures.

The following design decisions have been made in this section:

<tip name="Design Decision DD.030">
Console access will use local authentication as a last-resort access method, with local accounts hardened using strong passwords and dual-factor authentication.
<br><br>
Rationale: Console access is the final recovery path when all remote management methods fail. Using local authentication on the console avoids dependency on external AAA services during outages, while strong passwords and 2FA prevent unauthorised physical access from compromising the fabric.
</tip>
<br><br>




### CIMC Hardening




Cisco CIMC is the embedded server management for Cisco UCS C-Series servers and therefore also for Cisco APICs. The following general hardening measures are used:

User Management:

- Enable strong password enforcement and automatic password expiration
- Use LDAP remote authentication if possible

Network Security:

- Enable IP Blocking to block an IP after several unsuccessful login attempts
- Enable IP Filtering to allow CIMC access only from a restricted set of IP addresses

Communication Services:

- Configure NTP
- Enable HTTP to HTTPS redirection
- Replace self-signed certification by a trusted CA-signed certificate
- Enable SSH access
- Use SNMPv3 whenever possible

<info name="Info">Starting with release 3.1(3) FIPS mode is available in CIMC. See the Cisco IMC Configuration Guides for specific instructions.</info>



### SNMP




Cisco ACI supports both SNMPv2c and SNMPv3 for both polling (GET) and notifications (TRAP). Note that pushing changes via SNMP using GET operations is not supported in Cisco ACI, which significantly reduces the attack surface when enabling SNMP.

<info name="Info">SNMPv2c and SNMPv3 are disabled by default; they must be explicitly configured before they can be used.</info>

The following design decisions have been made in this section:

<tip name="Design Decision DD.031">
SNMPv3 will be used in preference to SNMPv2c wherever monitoring tools support it.
<br><br>
Rationale: SNMPv3 provides authentication and encryption, preventing credential exposure and data tampering. SNMPv2c transmits community strings in clear text, making it vulnerable to eavesdropping. Since ACI does not support SNMP-based configuration changes, the risk is limited to monitoring data, but SNMPv3 remains the security best practice.
</tip>
<br><br>




### Disable Unused Services




Cisco ACI is designed not to run non-required services by default, as well as to limit remote management services or protocols that are active by default. Hence, there is no action required from an administrator standpoint to disable them. If any other protocol is required, such as SNMP, administrator have to explicitly configure it.



### Disable USB Port




Nexus 9000 switches running Cisco ACI code have the USB port enabled by default, but can be disabled if required, e.g., in environments where physical access to the devices is not strictly controlled. This can be done with all switches of the fabric or individual for single switches.



### Backups




Periodic remote backups should be performed frequently enough to ensure minimal loss of configuration changes in case of a disaster.

<caption name="Encryption configuration data model">

```yaml
apic:
  fabric_policies:
    config_passphrase: passphrase
```
</caption>

For further info on how the Config Passphrase are defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/config_passphrase/).

<info name="Info">When AES encryption is not enabled, Cisco APIC will remove all sensitive information from the configuration file before exporting. Therefore, the configuration backup will not include passwords, keys, tokens, or other sensitive attributes. In such scenario, restoring the backup will result in some functionality not working correctly.</info>

The following design decisions have been made in this section:

<tip name="Design Decision DD.032">
Configuration backups will be encrypted using AES encryption with a configured config_passphrase.
<br><br>
Rationale: Without AES encryption, APIC strips sensitive information (passwords, keys, certificates) from backup exports, which prevents a full configuration restore. Enabling AES encryption preserves all sensitive data in the backup, ensuring that a restore operation can fully reconstruct the original configuration.
</tip>
<br><br>




### Securing the Control Plane







### Control-Plane Policing (CoPP)




CoPP is enabled by default and pre-configured with Cisco-calculated values that have been formulated and tested by Cisco engineering teams and proven to be sufficient in most fabric deployments.

However, there might be scenarios where additional tuning is needed. Therefore, the approach used is:

- Initially, use the default policy
- Monitor CoPP drops
- Modify CoPP thresholds only if drops increment constantly

<info name="Info">The following command can be used to check CoPP statistics per switch: vsh_lc -c 'show system internal aclqos brcm copp entries unit 0'. See chapter Control Plane Policing in the Security Configuration Guide for more details regarding CoPP and adjusting thresholds.</info>

The following design decisions have been made in this section:

<tip name="Design Decision DD.033">
CoPP will remain at its default Cisco-calculated values, and will only be adjusted if monitoring reveals sustained packet drops that affect fabric operation.
<br><br>
Rationale: Cisco CoPP defaults are calculated to protect the control plane under typical conditions. Modifying CoPP rates without evidence of a problem risks either weakening control-plane protection or dropping legitimate traffic. The recommended approach is to monitor CoPP counters and only tune values when persistent drops are confirmed.
</tip>
<br><br>




### Control-Plane Protocols Authentication




Authentication can be used in control plane protocols. Cisco ACI supports authentication for most control plane protocols, including NTP, BFD, OSPF, BGP, and EIGRP, as well as other protocols used internally, such as CooP.

<caption name="Protocol Authentication Overview">

| Protocol | Authentication Method |
| --- | --- |
| NTP | MD5, SHA1 |
| BFD | SHA1 |
| OSPFv2 | simple, MD5 |
| OSPF v3 | IPsec (supported since version 6.1(2)) |
| EIGRP | MD5 |
| BGP | MD5 |
| CooP | MD5 |

</caption>

<info name="Info">MD5 and SHA are no longer recommended for cryptographic purposes according to IETF. However, due to compatibility reasons they are still used. An expansion to newer methods is expected in the next ACI versions.
Check the release notes regularly and update accordingly.</info>

The following design decisions have been made in this section:

<tip name="Design Decision DD.034">
Authentication will be enabled for all control-plane protocols (NTP, BFD, OSPF, BGP, EIGRP, CooP) used in the fabric.
<br><br>
Rationale: Unauthenticated control-plane protocols are vulnerable to spoofing and injection attacks that could corrupt routing tables or disrupt fabric convergence. Enabling protocol authentication ensures that only trusted peers can form adjacencies and exchange routing information.
</tip>
<br><br>




### Restrict Infra VLAN Traffic




In some cases (e.g., using VMM features like Cisco ACI Container Network Interface) the extensions of the Infra VLAN outside of the ACI fabric is required. In those scenarios, the Infra VLAN can be protected by enabling the Restrict Infra VLAN Traffic option. This limits the allowed traffic to specific destinations to:

- DHCP/ARP/ICMP
- iVXLAN/VXLAN
- OpFlex

The following design decisions have been made in this section:

<tip name="Design Decision DD.035">
Restrict Infra VLAN Traffic will be enabled to limit the allowed traffic to specific destinations to DHCP/ARP/ICMP, iVXLAN/VXLAN, OpFlex.
<br><br>
Rationale: Restrict Infra VLAN Traffic limits the allowed traffic to specific destinations to DHCP/ARP/ICMP, iVXLAN/VXLAN, OpFlex. This helps to prevent unauthorized access to the Infra VLAN.
</tip>
<br><br>




### Fabric Internode Authentication




Cisco ACI supports two Internode Authentication Security modes which can be used to create relationship (including secure TLS-encrypted channels) between all devices.

Permissive Mode:

- SSL certificates are not validated
- Serial number validation is not enforced
- Controllers are automatically authorized to join the fabric
- Switches must be manually authorized to join the fabric

Strict Mode:

- SSL certificates are validated
- Serial Number validation is enforced
- Controllers and switches must be manually authorized to join the fabric

The following design decisions have been made in this section:

<tip name="Design Decision DD.036">
Fabric internode authentication will be configured in Strict Mode to require SSL validation and serial-number enforcement for all devices joining the fabric.
<br><br>
Rationale: Strict Mode prevents unauthorised or rogue devices from being admitted to the fabric by enforcing SSL certificate validation and serial-number checks. Permissive Mode skips these checks, which could allow a compromised or unknown device to join the fabric and intercept control-plane traffic.
</tip>
<br><br>




### Securing the Data Plane







### General Data Plane Hardening




The following general hardening measures apply to all Data Center networks. Some of these are already enforced in Cisco ACI by default and hence no action is required from the administrator point of view.

<caption name="General Data Plane Hardening">

| Function | Default | Comment | Action |
| --- | --- | --- | --- |
| IP Source Routing | disabled | not supported by ACI | no action required |
| IP Directed Broadcast | disabled | not supported by ACI | no action required |
| Storm Control | enabled with rate 100% | 100% effectively disables storm-control | adopt rate based on requirements |
| IP Fragments | discard IP Fragments | recommended to filter on top of any ACL | create filter if IP Fragments required |

</caption>

The following design decisions have been made in this section:

<tip name="Design Decision DD.037">
Default ACI data-plane hardening features will be preserved, and additional hardening settings will be reviewed and applied per the fabric-specific requirements table.
<br><br>
Rationale: ACI enforces several data-plane hardening measures by default (e.g. DHCP relay validation, ARP inspection). Preserving these defaults ensures a strong baseline security posture. Additional settings should be reviewed against the specific deployment to avoid disabling protections or enabling options that conflict with the design.
</tip>
<br><br>




### Protecting from Loops




Cisco ACI does not participate in Spanning Tree Protocol (STP). However, Bridge Protocol Data Units (BPDUs) are forwarded transparently through the fabric between EPGs.

The MisCabling Protocol (MCP) provides additional protection against loops due to misconfigurations. When a loop is detected, MCP will generate faults, events, and syslog messages to inform about the situation. MCP can be enabled globally and per-interface. By default, it is disabled globally and enabled on each port. For MCP to work, it must be enabled globally, regardless of the per-interface configuration.

<info name="Info">Even if MCP detects loops per VLAN, if MCP is configured to disable the link and if a loop is detected in any of the VLANs present on a physical link, MCP then disables the entire link. For more information, see chapter MisCabling Protocol (MCP) in Cisco ACI Design Guide.</info>

The following design decisions have been made in this section:

<tip name="Design Decision DD.038">
MCP should be enabled on all ports facing external devices, and per-VLAN MCP on those interfaces where it adds extra value (enabling per-VLAN MCP in all ports may not be supported depending on the scale of the fabric).
<br><br>
Rationale: MCP provides additional protection against loops due to misconfigurations. When a loop is detected, MCP will generate faults, events, and syslog messages to inform about the situation. MCP can be enabled globally and per-interface. By default, it is disabled globally and enabled on each port. For MCP to work, it must be enabled globally, regardless of the per-interface configuration.
</tip>
<br><br>




### Anti-Spoofing




<caption name=" - Overview Anti-Spoofing Mechanisms">

| Function | Description | Recommendation | Reference |
| --- | --- | --- | --- |
| Enforce Subnet Check | Checks IP learning on VRF level to prevent IP spoofing | Enable | [ACI Endpoint Learning White Paper](https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-739989.html#EnforceSubnetCheck) |
| Port Security | Protects the fabric from being flooded with unknown MAC addresses by limiting the number of MAC addresses per port | Evaluate carefully the need based on specific risk assessment | [Port Security Configuration Guide](https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/security-configuration/cisco-apic-security-configuration-guide-60x/port-security-60x.html) |
| IEEE 802.1X | Permit or deny network connectivity based on the end user or device connected to the port | Evaluate use cases and enable if required | [802.1X Configuration Guide](https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/security-configuration/cisco-apic-security-configuration-guide-60x/802-1x-60x.html) |
| First Hop Security | Collection of features: IP inspection, Source Guard, Router Advertisement Guard | Evaluate use cases and enable if required | [First Hop Security Configuration Guide](https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/security-configuration/cisco-apic-security-configuration-guide-60x/first-hop-security-60x.html) |

</caption>



### MACsec




MACsec is an IEEE 802.1AE standard-based Layer 2 hop-by-hop encryption that provides data confidentiality and integrity for media access independent protocols. The 802.1AE encryption with MACsec Key Agreement (MKA) Protocol is supported on all types of links.

Must Secure Mode - only allows encrypted traffic on the link

Should Secure Mode - allows both clear and encrypted traffic on the link

<info name="Info">Before deploying MACsec in Must Secure mode, the keychain must be deployed on the affected links, or the links will go down. To address this issue MACsec should be initially deployed in Should Secure mode and once all the links are up the security mode is changed to Must Secure. For more information see chapter MACsec in Cisco APIC Layer 2 Networking Configuration Guide.
</info>



## Hardening and Security



The following sections detail the hardening and security measures applied to the %%customerName ACI fabric across the management, control, and data planes.



### Management Plane



Content for Management Plane hardening measures goes here.



### Control Plane



Content for Control Plane hardening measures goes here.



### Data Plane



Content for Data Plane hardening measures goes here.



### Security Requirements Summary



IT security requirements for Cisco ACI can come from different sources (e.g., ISO 27001) and coordinated with the responsible departments, usually the CISO. The following table contains a list of the requirements (controls) to be implemented in %%customerName's environment.

<caption name="ACI-FABRIC-NAME - Security Requirements - ISO 27001">

| ID | Requirement | Implementation | Source | In Compliance? | Comment |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

</caption>






# System Settings



<warning name="Warning">The following settings are configured under the assumption that these features are being deployed in a greenfield environment. Applying these settings in a live environment may be disruptive and therefore should be carefully planned.</warning>



## Fabric Wide Settings



Any policy configured in the Fabric-Wide Settings is pushed to each Leaf switch as it initializes. There are a number of recommended features that are applied here.



### Remote EP Learning



The ability to disable Remote End Point Learning was brought in to address an issue seen with Gen1 Leaf Switches and is only applicable if these exist anywhere within a particular ACI Fabric. If all of the Leaf switches are Gen2 or above, then this feature should not be implemented (e.g., Disable Remote EP Learning is left as 'unchecked').

ACI Leaf Nodes learn the MAC/IP Address of 'Remote' EPs when packets arrive via a Spine Node (i.e., the EP is located on a different Leaf Node). Disabling this learning prevents a situation that can occur with first-generation switches, where IP EPs on a non-Border Leaf send traffic to EPs connected to the Border Leaf, but then move to a different Leaf switch (e.g., following vPC failover). If the EP is also sending traffic to the L3Out (whose VRF is configured for 'ingress policy enforcement' - the default), during the move, then the original Remote EP entry on the Border Leaf would continue to be incorrectly refreshed (pointing at the first/incorrect Leaf switch). When this feature is implemented (Remote End Point Learning is Disabled), Border leaf switches no longer learn Remote EPs, and therefore there cannot be any stale entries.

By default, Remote EP Learning is enabled in Border Leafs, but this feature allows it to be disabled.

<info name="Info">This feature does NOT disable the learning of remote MAC addresses.</info>

Remote EP Learning is relevant to Gen1 Leaf switches with L3Outs (e.g., Border Leaf switches). Whether this feature should be enabled/disabled, depends upon the particular environment, as follows:

1. Disable Remote EP Learning should be Checked (Disabling the learning of Remote EP's) in the following circumstances:
- when there is a mix of Gen1 and Gen2 (or later) Leaf switches AND there are non-dedicated Border Leaf switches (Leaf switches with L3Outs that also have Local hosts connected).
- OR, when a L3Out Bridge Domain is stretched across different Border Leaf switches (regardless of 1st or 2nd generation switches) that are NOT part of the same vPC peer (e.g. Multi-Pod with each Pod has a firewall (in Active/standby mode), connected through the same L3Out using an SVI on the same stretched BD).

This feature requires Tenant / Networking / VRF / Policy Control Enforcement set to 'Ingress' on VRF (this is the default setting).

<info name="Info">Dedicated Border Leaf switches are implemented when possible to simplify troubleshooting and visualize the traffic paths, although this can be cost-prohibitive for some smaller Fabrics.</info>

Disable Remote EP Learning should be left as the default and remain Unchecked (Enabling the learning of Remote EP's) when there are ONLY Gen2 (or later) Leaf switches or later in the Fabric, and the L3Out BD does not have the topology described above.

In the %%customerName ACI design, Disable Remote EP Learning will be left 'unchecked'.

<info name="Info">System / System Settings / Fabric Wide Setting / Disable Remote EP Learning.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Disable Remote EP Learning setting needs to be defined in the input files:

<caption name="Disable Remote EP Learning Data Model">

```yaml
apic:
  fabric_policies:
    global_settings:
      disable_remote_endpoint_learn: false
```
</caption>

For further information on how the Disable Remote EP Learning setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fabric_wide_settings/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.039">
The Remote EP Learning setting will be left unchecked (disabled) unless Gen1 leaf switches are present in the fabric with specific topology conditions.
<br><br>
Rationale: This setting is only required when Gen1 leaf switches coexist with Gen2 switches or when stretched L3Out BDs span Gen1 leaves. In those scenarios, stale remote EP entries on Gen1 hardware can cause traffic black-holes. When the fabric is Gen2-only, enabling this setting is unnecessary and would add operational complexity.
</tip>
<br><br>




### Enforce Subnet Check



When enabled, the ACI Leaf will only learn the IP and MAC address for a new Local EP entry when the source IP of the incoming packet belongs to one of the ingress BD subnets.

- This feature is a global setting, and by default is Disabled.
- When enabled, this feature applies to all BDs in all VRFs.
- When this feature is enabled, ACI flushes all local EP entries (IP and MAC) for EP's with a source IP that does not belong to any BD subnets, and all remote EPs that have IP's outside of the VRF (such as an IP address that exists behind the L3Out).

This feature protects the Global Switching Table by not installing a Local or Remote EP (IP and MAC address) entry if the Source IP address is not valid, e.g., from an EP that is spoofing IP addresses.

This feature should be used instead of 'Limit IP Learning to Subnet' at the BD level, which is not required if this feature is enabled. In addition, this feature is superior, as 'Limit IP Learning to Subnet' only prevents the learning of the IP address, whereas this feature prevents the learning of the MAC address also.

<info name="Info">'Enforce Subnet Check' is not a First Hop Security feature (like Source Guard) in that it does not protect against a machine that is spoofing IP addresses within the BD subnets.</info>

In the %%customerName ACI design, Enforce Subnet Check will be enabled.

<info name="Info">System / System Settings / Fabric Wide Setting / Enforce Subnet Check.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Enforce Subnet Check setting needs to be defined in the input files:

<caption name="Enforce Subnet Check Data Model">

```yaml
apic:
  fabric_policies:
    global_settings:
      enforce_subnet_check: true
```
</caption>

For further information on how the Enforce Subnet Check setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fabric_wide_settings/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.040">
Enforce Subnet Check will be enabled to restrict local endpoint learning to valid ingress BD subnets.
<br><br>
Rationale: Enabling this setting protects the Global Switching Table by preventing endpoints from being learned with IP addresses that do not belong to any configured BD subnet. This mitigates MAC/IP spoofing attacks and ensures that only legitimate traffic is forwarded within the fabric.
</tip>
<br><br>




### Enforce EPG VLAN Validation



When enabled, the system globally prevents overlapping VLAN pools from being assigned to EPGs.

If there are any overlapping pools allocated within any EPG in APIC, then this feature cannot be enabled (an error is displayed if there is an attempt to enable it).

If no existing overlapping pools are present, then this feature can be enabled. Once enabled, when an attempt to allocate a domain on an EPG is performed, and the domain contains a VLAN pool with a range overlapping with another domain already associated with the EPG, then the configuration is blocked.

When overlapping VLAN pools exist under an EPG, then the FD VNID allocated for the EPG by each switch is non-deterministic and different switches may allocate different VNIDs. This can cause EPM sync failures between leafs within a vPC domain (causing intermittent connectivity for all endpoints within the EPG). It can also cause bridging loops if the user is extending STP between the EPG, as the BPDUs will be dropped between switches due to FD VNID mismatch.

In the %%customerName ACI design, Enforce EPG VLAN Validation will be checked.

<info name="Info">System / System Settings / Fabric Wide Setting / Enforce EPG VLAN Validation.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Enforce EPG VLAN Validation setting needs to be defined in the input files:

<caption name="Enforce EPG VLAN Validation Data Model">

```yaml
apic:
  fabric_policies:
    global_settings:
      overlapping_vlan_validation: true
```
</caption>

For further information on how the Enforce EPG VLAN Validation setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fabric_wide_settings/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.041">
Enforce EPG VLAN Validation will be enabled to prevent overlapping VLAN pool assignments across EPGs.
<br><br>
Rationale: Without this check, overlapping VLAN pools can cause non-deterministic FD VNID allocation, leading to EPM sync failures and potential bridging loops. Enabling EPG VLAN Validation catches these misconfigurations at deployment time, preventing hard-to-diagnose forwarding issues in production.
</tip>
<br><br>




### Reallocate GIPo



Each BD is assigned one Class-D IP from the Global IP outside (GIPo) multicast pool, to be used for Broadcast, Unknown Unicast & Multicast traffic (BUM). When enabled, this feature ensures that the GIPo of stretched BDs does not overlap with that of non-stretched BDs. If this is a new ACI installation, then ACI will automatically use separate GIPo pools for stretched and non-stretched BDs, however, if this is an upgrade, and the GIPos have already been assigned using the original method, then enabling this feature will allow ACI to reallocate the GIPos to ensure they do not overlap.

By default, this feature is disabled.

When ACI Multi-site is deployed, there is a possibility that BDs stretched between sites will be assigned the same GIPo as non-stretched BDs.

This feature relates to ACI Multi-site but should be enabled even in non-multi-site deployments in case the customer uses that feature in the future.

In the %%customerName ACI design, Reallocate GIPo will be checked.

<info name="Info">System / System Settings / Fabric Wide Setting / Reallocate GIPo.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Reallocate GIPo setting needs to be defined in the input files:

<caption name="Reallocate GIPo Data Model">

```yaml
apic:
  fabric_policies:
    global_settings:
      reallocate_gipo: true
```
</caption>

For further information on how the Reallocate GIPo setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fabric_wide_settings/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.042">
The Reallocate GIPo setting will be enabled to prevent overlapping multicast group assignments between stretched and non-stretched Bridge Domains in Multi-Site deployments.
<br><br>
Rationale: Without GIPo reallocation, stretched and non-stretched BDs may receive overlapping GIPo multicast addresses, causing BUM traffic to be delivered to incorrect endpoints across sites. Enabling this setting ensures proper multicast address separation, which is a prerequisite for correct Multi-Site BUM forwarding.
</tip>
<br><br>




### Enforce Domain Validation



When enabled, this feature ensures that an EPG cannot be assigned to a port if the EPG has not been associated to a Domain. By default, this feature is disabled.

If an EPG has been created, but has not yet been assigned to a Domain, ACI will (by default) still allow the EPG to be assigned to a port. In this instance, ACI will raise an error and communications to/from the port will fail. This is expected (and desired) behavior as the ACI security policy is unable to assign a VXLAN ID for Fabric encapsulation if it cannot map the EPG VLAN to the Port's AAEP allowed VLAN list.

In the %%customerName ACI design, Enforce Domain Validation will be checked.

<info name="Info">System / System Settings / Fabric Wide Setting / Enforce Domain Validation.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Enforce Domain Validation setting needs to be defined in the input files:

<caption name="Enforce Domain Validation Data Model">

```yaml
apic:
  fabric_policies:
    global_settings:
      domain_validation: true
```
</caption>

For further information on how the Enforce Domain Validation setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fabric_wide_settings/).



### Opflex Client Authentication



Opflex is the protocol used by ACI to communicate its policy with external devices (e.g., GOLF routers or Linux hosts). This feature increases the security of the SSL-encrypted Opflex connection by adding Client Certificate-based Authentication. Prior to this feature, there was no authentication between the peers. By default, on new installations of ACI 2.3 and higher, this feature is enabled, but is disabled on earlier versions, and continues to remain disabled when upgrading from earlier versions, in order to remain compatibility.

This feature is relevant to environments currently using, or potentially will be peering between an ACI Fabric and Opflex clients.

This feature provides additional security between Opflex peers by using SSL certificates for client authentication.

In the %%customerName ACI design, Opflex Client Authentication will be left at the default of the deployed ACI release (enabled). It could be disabled in the future, should the need arise due to the lack of support within the Ubuntu/Redhat/etc, OpenStack client, for instance.

<info name="Info">System / System Settings / Fabric Wide Setting / Opflex Client authentication.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Opflex Client Authentication setting needs to be defined in the input files:

<caption name="Opflex Client Authentication Data Model">

```yaml
apic:
  fabric_policies:
    global_settings:
      opflex_authentication: true
```
</caption>

For further information on how the Opflex Client Authentication setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/fabric_wide_settings/).



## APIC Connectivity Preferences



This policy dictates which ports the APICs will use when initiating management traffic to external management devices (e.g., for AAA or SNMP).

- Out-of-band (OOB) management ports are the two LAN-on-Motherboard (LOM) ports.
- In-band management ports are the two PCIE VIC uplink ports that connect to the leaf nodes.

The default setting is for the APIC to prefer the in-band path if it is available, however, a dedicated out-of-band network is recommended. This becomes a mandatory requirement for ACI Multi-Site.

<info name="Info">The APIC will always reply using the interface on which traffic was received (e.g., if SNMP polls arrived on the OOB interface, APIC will respond using this interface, even if the preferred interface is set to in-band).
The corresponding policy (relevant contracts within the mgmt tenant) should be configured.</info>

VMM integration and Multi-Site have dependencies on this setting:

- VMware vCenter must be able to reach the APIC's management IP address via this path.
- Multi-Site requires this to be set to ooband.

In the %%customerName ACI design, APIC Connectivity Preference will be set to ooband.

<info name="Info">System/System Settings/APIC Connectivity Preferences.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the APIC Connectivity Preference is defined in the input files:

<caption name="Apic Connectivity Preference Data Model">

```yaml
apic:
  fabric_policies:
    apic_conn_pref: ooband
```
</caption>

For further information on how the APIC Connectivity Preference is defined in the IaC data model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/apic_connectivity_pref/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.043">
APIC Connectivity Preferences will be set to out-of-band (ooband) so that external management traffic uses the dedicated management network.
<br><br>
Rationale: Setting connectivity to ooband ensures APIC management traffic (NTP, DNS, RADIUS/TACACS+, syslog) is routed through the dedicated OOB management port rather than through the fabric data plane. This is mandatory for ACI Multi-Site and eliminates circular dependencies where fabric issues could disrupt management access.
</tip>
<br><br>




## Fabric Security



The Federal Information Processing Standards (FIPS) Publication 140-2, Security Requirements for Cryptographic Modules, details the U.S. government requirements for cryptographic modules. FIPS specifies certain cryptographic algorithms as secure, and it also identifies which algorithms are used if a cryptographic module is to be called FIPS compliant.

When FIPS is enabled, it is applied across Cisco APICs.

<info name="Info">System / System Settings / Fabric Security.</info>

In the %%customerName ACI design, the FIPS mode will be set to Disabled.



## Global AES Passphrase Encryption



By default, when exporting fabric configurations, secure properties (passwords and certificates) are not included. To export any secure properties, AES encryption must be configured and enabled. The global AES encryption setting is applicable to all import and export operations.

<note name="Note">When restoring a fabric by importing an encrypted configuration, the passphrases must match.</note>

<info name="Info">System/System Settings/Global AES Passphrase Encryption Settings.</info>

In the %%customerName design, the global AES encryption is enabled in the fabric.



## Control Plane MTU



In ACI Multi-Pod and Multi-Site environments, endpoint reachability is exchanged between Pods/Sites by the Control Plane, using MP-BGP EVPN. The Control Plane MTU Policy sets the global MTU size for Control Plane packets sent by the ACI Nodes. The default value for the Control Plane MTU is 9000 Bytes. The MTU size may need to be changed, if required, due to the MTU supported by the IPN. The supported values are between 1500 to 9216 bytes.

This feature is relevant to ACI Multi-Pod & Multi-Site environments where Control Plane traffic must traverse an IPN/ISN.

<info name="Info">Whereas Data Plane traffic must be encapsulated in VXLAN (54 bytes overhead) across pods, Control Plane traffic is not, and therefore the Control Plane MTU value can be set to the maximum MTU supported by the IPN.</info>

This setting is left at the default (9000 bytes), unless there is a restriction of the MTU supported by the service provider of the inter-pod/site links for Multi-Pod/Multi-Site environments.

In the %%customerName ACI design, since %%customerName has full control of the IPN/ISN infrastructure, and therefore of the MTU across the IPN/ISN, the default value of the Control Plane MTU (9000 bytes) will be used.

<info name="Info">The Control Plane MTU setting should not be mistaken with the Fabric L2 MTU Policy under Fabric - Fabric Policies - Policies - Global, which is the one that determines the MTU of the front panel access ports. In other words, if your servers are sending packets with an MTU of 9050 bytes, then this is the setting that you should modify to account for that data plane MTU requirement.
The Fabric L2 MTU policy is a fabric-wide layer 2 setting. It affects all L2 ports in the fabric. The default value is 9000 bytes. It does not have any impact on the MTU that you configure for L3 ports (non-switchport), defined in L3Outs.
System / System Settings / Control Plane MTU.
</info>



## BGP Route Reflector




In order to redistribute external IPv4 & IPv6 routes from Border / Service Leaf switches, ACI uses MP-iBGP (Multi-Protocol internal Border Gateway Protocol) and Route Reflection between the Leaf and Spine Nodes. The configuration of BGP Route Reflectors is mandatory in order to enable IP routing between the Fabric, and external devices.

Configuration of the BGP Route Reflector Policy requires an Autonomous System Number (ASN) to be defined for the Fabric as a whole. All Spine Nodes per Pod should be selected as Route Reflector Nodes. ACI will internally select two of these as 'active' Route Reflectors, leaving the remaining Spines as 'passive.' The ASN can be in 4-byte ASPLAIN format, from 1 to 4294967295. The ASN assigned to different Fabrics in a Multi-Site setup can be identical or different - both are supported.

Once the 'default' BGP Route Reflector Policy is configured with the ASN & the Route Reflector Nodes, it is automatically applied to the fabric via the Pod Policy Group (Fabric / Fabric Policies / Pods / Pod-Policy-Group). This will result in iBGP sessions being automatically established between the Spine Route-Reflectors and all of the Leaf Nodes, which can be verified at Fabric / Inventory / PodX / <Spine Node> / Protocols / BGP / BGP for VRF-overlay-1 / Neighbors.

The configuration of this Policy is mandatory in order to enable IP Routing between the ACI Fabric and external devices (i.e. using a L3Out). Each ACI Pod is configured with its own group of Route Reflectors.

In the %%customerName ACI design, the corresponding BGP Autonomous System will be defined for each fabric and the two spines of each data center will be set as Route Reflector nodes.

<caption name="ACI-FABRIC-NAME - ACI fabric BGP AS Route Reflector Nodes">

| ACI fabric | BGP AS | Route Reflector Nodes |
| --- | --- | --- |
| ACI-FABRIC-NAME | N/A | N/A |

</caption>

<info name="Info">System / System Settings / BGP Route Reflector.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the BGP Route Reflector setting needs to be defined in the input files:

<caption name="Bgp Route Reflector Data Model">

```yaml
apic:
  fabric_policies:
    fabric_bgp_as: 65011
    fabric_bgp_rr:
      - 111
      - 112
      - 121
      - 122
    fabric_bgp_ext_rr:
      - 101
      - 201
```
</caption>

For further information on how the BGP Route Reflector setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/bgp_policy/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.044">
All spine switches will be configured as BGP Route Reflector nodes, with two active and the remainder in passive standby.
<br><br>
Rationale: Configuring all spines as Route Reflectors ensures that any spine can assume the active RR role if a failure occurs. Having two active RRs provides redundancy for MP-iBGP route distribution, while passive nodes are ready to take over without requiring configuration changes, maintaining fabric convergence during spine failures.
</tip>
<br><br>




## COOP Group



When an EndPoint (EP) is learned by a Leaf switch, the Leaf forwards the EP IP and MAC address information to one of the Spine switches using Zero Message Queue (ZMQ). The Council of Oracle Protocol (COOP) is used between the Spine nodes to ensure they all have a consistent copy of EP address and location information, and to maintain the Distributed Hash Table (DHT) repository of endpoint identity to location mapping database.

From ACI 2.0, COOP was enhanced to support MD5 authentication to protect COOP messages from potential malicious traffic injection. The APIC provides the MD5 'token' automatically, which is a string that changes every hour, and cannot be displayed. In order to continue to support legacy connectivity as well as the new functionality, two ZMQ authentication modes are now supported: strict and compatible.

- Strict mode: COOP allows MD5 authenticated ZMQ connections only. This is the recommended setting for all ACI Fabrics running version 2.0 or above.
- Compatible mode: COOP accepts both MD5 authenticated and non-authenticated ZMQ connections for message transportation. This is the default setting.

In the %%customerName design, the COOP Group Policy will be set to 'Strict Type'.

<info name="Info">System / System Settings / COOP Group.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the COOP Group policy needs to be defined in the input files:

<caption name="Coop Group Data Model">

```yaml
apic:
  fabric_policies:
    coop_group_policy: strict
```
</caption>

For further information on how the COOP Group policy is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/coop_policy/).



## Endpoint Controls



Endpoint Controls are system-level settings that govern how the ACI fabric handles endpoint learning, loop detection, and rogue endpoint situations. These controls are configured under System > System Settings > Endpoint Controls.



### Endpoint Loop Protection



The Endpoint Loop Protection feature is a fabric-level policy used to detect potential Layer 2 loops in network segments that are connected to ACI.

<info name="Info">This feature does not take effect if Rogue Endpoint Control is enabled, which is preferred.</info>

When enabled, ACI monitors frequent Endpoint MAC address moves from one Leaf port to another. If ACI detects that an EP has moved more than the permitted number of times (within the detection interval), it will take one of two actions:

- Disable EP learning within the specific BD.
- Disable the port that the EP is connected to.

By default, the feature is disabled, but when enabled with the default settings, ACI will disable the port if an EP moves 4 times within 60 seconds. The Loop Detection Interval specifies the number of seconds (range 30-300 seconds) within which an EndPoint moves ports. The Loop Detection Multiplication Factor is the number of times (from 1 to 255) the EP must move between ports, within the Loop Detection Interval.

Rogue Endpoint Control is preferred over this feature. If Rogue Endpoint detection is enabled, then this feature does not take effect, even if it has been enabled. Although both features detect a Layer 2 Loop, their action is different. EP Loop Protection will shut down a Leaf port (attempting to remove the loop) or disable learning on the BD, whereas Rogue EP Detection is less drastic and will only stop the relevant EP(s) from being learned. Per-VLAN MCP is the preferred way of detecting a loop and disabling the port, in conjunction with Rogue EP Control.

In the %%customerName ACI design, EP Loop Protection will be left disabled with the default action of Port Disable, with default timers.

<info name="Info">System / System Settings / Endpoint Controls / EP Loop Protection.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the EP Loop Protection setting needs to be defined in the input files:

<caption name="Endpoint Loop Protection Data Model">

```yaml
apic:
  fabric_policies:
    ep_loop_protection:
      admin_state: true
      detection_interval: 180
      detection_multiplier: 10
      action: port-disable
```
</caption>

For further information on how the EP Loop Protection setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/ep_loop_protection/).



### Rogue EP Control



The Rogue EP Control feature attempts to detect a situation where a rogue EP attempts to attack Leaf switches by repeatedly injecting packets on different ports and changing 802.1Q tags (emulating an EP moving between ports at a high frequency). This situation can also occur due to misconfigurations on the EP (host). Such rapid movement in the fabric can cause high CPU usage and significant instability.

When enabled, and the fabric detects enough MAC or IP moves within the detection interval, then the MAC address of the EP is statically programmed on one of the Leaf ports, and traffic is dropped to and from the rogue endpoint for the length of the Hold Interval. In addition, a fault is raised on the Leaf switch.

By default, this feature is disabled.

<info name="Info">This feature is not supported on Remote Leaf switches or Cisco ACI Multi-Site.</info>

When Rogue EP Control is enabled, EP Loop Protection does not have effect. It is the preferred method to detect loops. Although both features detect a Layer 2 Loop, their action is different. EP Loop Protection will shut down a Leaf port (attempting to physically remove the loop) or disable learning for the entire BD, whereas Rogue EP Detection is more granular and will only stop traffic to/from those EPs that are moving ports, leaving other traffic unaffected.

In order to detect and break a loop, per-VLAN MisCabling Protocol (MCP) is used along with this feature.

In the %%customerName ACI design, Rogue EP Control will be enabled. The default timers will be relaxed a little. The settings will be:

- Detection Interval = 60 seconds.
- Multiplication Factor = 10.
- Hold interval = 1800 seconds.

<info name="Info">System/System Settings/Endpoint Controls/Rogue EP Control.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Rogue EP Control setting needs to be defined in the input files:

<caption name="Rogue EP Control Data Model">

```yaml
apic:
  fabric_policies:
    rogue_ep_control:
      admin_state: false
      detection_interval: 60
      detection_multiplier: 10
      hold_interval: 1800
```
</caption>

For further information on how the Rogue EP Control setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/rogue_ep_control/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.045">
Rogue Endpoint Control will be enabled with a detection interval of 60 seconds, a multiplication factor of 4, and a hold interval of 1800 seconds.
<br><br>
Rationale: Rogue EP Control detects endpoints that rapidly move between ports or leavesâ€”behaviour indicative of an attack or misconfigurationâ€”and quarantines them. The configured timers balance detection speed against false positives, and the 1800-second hold interval prevents a flapping endpoint from repeatedly disrupting the forwarding table.
</tip>
<br><br>




### IP Aging



ACI dynamically ages out Local and Remote Endpoint (EP) database entries based upon an idle timer. By default, when an EP (source MAC or IP) gets a 'hit,' ACI will refresh all IP addresses associated with the same MAC address.

When this feature is enabled, ACI will send three ARP requests (IPv4) and neighbor solicitations (IPv6) to potential stale IP addresses, if they have reached 75% of the configured Aging Interval. If replies are not received, then those IP addresses will be removed independently. By default, this feature is disabled.

This feature is especially useful in environments that contain devices such as Load balancers that perform NAT. Here, a single MAC address may be associated with many IP addresses, some of which will be de-commissioned during the natural life cycle of the device. Without this feature enabled, these old IP addresses will continue to remain in the EP database.

The individual timers that control how EP entries are aged out can be modified via the Endpoint Retention Policy within the individual Tenant Policies and applied at the BD and VRF level as required. By default, the common/Policies/Protocol/End Point Retention 'default' policy in the common tenant is used, which has a default of 300 seconds.

In the %%customerName ACI design, IP Aging will be enabled, using the default Common Tenant 300s Aging Interval.

<info name="Info">System / System Settings / Endpoint Controls / IP Aging.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the IP Aging setting needs to be defined in the input files:

<caption name="IP Aging Data Model">

```yaml
apic:
  fabric_policies:
    ip_aging: true
```
</caption>

For further information on how the IP Aging setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/ip_aging/).



## Load Balancer



The ACI fabric provides several options for load balancing the traffic from Leaf to Spine among the available uplinks. The ACI fabric redistributes traffic when the number of available links changes due to a link going off-line or coming on-line. In all modes of load balancing (static or dynamic) the traffic is sent only on those uplinks or paths that are equal and the lowest cost from a routing perspective (ECMP). The load balancing modes are selected within the 'default' Load Balancer Policy, as follows:

- Dynamic Load Balancing Mode (DLB) - this adaptive mode distributes traffic based upon end-to-end congestion. DLB places different flowlets (a group of continuous packets from the same IP flow) onto different links, based upon the gaps between flowlets. Whilst DLB is not always able to provide optimal load-balancing, it is never worse than static hash load-balancing (default method), and in the majority of cases provides an application performance benefit.

<info name="Info">Placing different flowlets of the same IP flow on different uplinks should not cause TCP re-ordering if the flowlet timeout value is greater than the maximum delay difference between any set of parallel paths.</info>

DLB can be:

- Aggressive - Shorter inter-flowlet gap, which is optimal for the distribution of traffic, but some packet re-ordering may occur, however, the overall benefit to application performance is equal or better than the Conservative mode.
- Conservative - Longer inter-flowlet gap, which guarantees that packets are not re-ordered, but provides less granular load-balancing due to less flowlet opportunities.
- Off - default.

<info name="Info">For Gen1 hardware, DLB & DPP are mutually exclusive. If DLB Aggressive or Conservative is chosen, then the Load Balancing mode must be set to 'Traditional,' and Dynamic Packet Prioritization must be 'Off.'</info>

- Dynamic Packet Prioritization (DPP) this dynamic mode, whilst not a load balancing technology, uses some of the same mechanisms in the switch hardware to prioritize short flows over long flows; a short flow is less than approximately 15 packets. Because short flows are generally more sensitive to latency than long ones, DPP can improve overall application performance. DPP can be:
- Off - default.
- On.

<info name="Info">For Gen1 hardware, DLB & DPP are mutually exclusive. If DPP is 'On,' then the Load Balancing mode must be set to 'Traditional,' and Dynamic Load Balancing must be set to 'Off.'</info>

- Load Balancing Mode is a static hashing method of load balancing traffic with the following two options:
- Traditional - (Default) -when a link goes down, traffic on all links is redistributed based on the new number of ports.
- Link Failure Resiliency - when a link goes down, the traffic destined to that link is distributed across the remaining links, and the existing traffic on the remaining links is unchanged.

The traditional static-hash load balancing method allocates flows to uplinks based on their 5-tuple (source/dest IP and port, plus protocol). With a large number of flows of equal size, this will provide a roughly equal distribution, however, it does not account for the level of traffic sent by each flow. In a common congestion scenario, a few large flows cause large queues to build-up at a bottleneck port, which significantly increases the latency for small flows traversing the same port. Using Dynamic load balancing adjusts traffic allocations (even within the same TCP flow) according to congestion levels, ensuring an optimal load-balancing across all uplinks.

In the %%customerName ACI design, DLB (Conservative) will be enabled in order to provide a better balancing method than the default static hash and to prevent TCP re-ordering. The 'Traditional' Load-Balancing mode will also be enabled (it has to be when using DLB) in order to optimize the load-balancing of traffic across the Spine links.

<info name="Info">System / System Settings / Load Balancer.
</info>



## PTP and Latency Measurement



Precision Time Protocol (PTP) is a time synchronization protocol defined in IEEE 1588, for nodes distributed across a network. Its hardware timestamp feature provides greater accuracy than other time synchronization protocols such as Network Time Protocol (NTP).

PTP is a distributed protocol that specifies how real-time PTP clocks in the system synchronize with each other. These clocks are organized into a master-member synchronization hierarchy with the grandmaster (GM) clock, the clock at the top of the hierarchy, determining the reference time for the entire system. PTP operates within a logical scope called a PTP domain. When PTP is enabled globally in an ACI fabric, it is automatically enabled on specific interfaces on all supported nodes. In the absence of an external GM clock, one of the Spine nodes is chosen as the GM and assigned a different priority from the other nodes (Slaves). If an external PTP GM clock is connected to the Spines, then the Master (M) Spine syncs to the GM, and acts as M to the Slave nodes.

The protocol administrative state. The state can be:

- Disabled - NTP time is used to sync the fabric.
- Enabled - A Spine is automatically chosen as a master to which the entire Fabric gets synchronized.

The default is Disabled.

Enabling PTP allows ACI to measure Fabric Latency, which is a valuable troubleshooting tool to monitor the time taken by a packet to traverse from source to destination in the fabric. The use of PTP enables micro-second accuracy, whereas NTP only has millisecond precision.

**PTP Considerations**

- An External GM clock is mandatory for PTP in a Multi-Pod scenario, though Spine Nodes can act as the PTP master in a non-Multi-Pod network.
- All the Spine nodes in the fabric should have EX or FX based line cards to support PTP. PTP and the Latency feature is not supported on any Gen1 Nodes. In the presence of non-EX/FX Nodes in the fabric, the external GM connectivity should be provided to all the Spines to ensure that the PTP time is synced across all the supported Leaf switches.
- NTP cannot coexist with PTP on a Cisco Nexus 9000 series switch, so either NTP is used (in which case Latency cannot be measured), or PTP is used.
- PTP must be enabled, and all nodes must be synchronized, in order for the Fabric Latency feature (to allow the fabric to measure EP to EP latency etc.) to be used. Fabric Latency Policies are configured within the Tenant/ Troubleshooting Policies/ Atomic Counter and Latency Policy GUI.

In the %%customerName ACI design, PTP will not be enabled initially. However, if in the future it is required, for instance, if Nexus Dashboard Insights is deployed, it could be enabled. In that case, no external GM clock would be used.

<info name="Info">System / System Settings / Precision Time Protocol.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the PTP and Latency Measurement setting needs to be defined in the input files:

<caption name="PTP Configuration Data Model">

```yaml
apic:
  fabric_policies:
    ptp:
      admin_state: true
      global_domain: 1
```
</caption>

For further info on how the PTP and Latency Measurement setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/ptp/).

The following design decisions have been made in this section:

<tip name="Design Decision DD.046">
PTP will not be enabled initially but may be enabled later if Nexus Dashboard Insights is deployed, provided all spine nodes have EX/FX or later line cards.
<br><br>
Rationale: PTP requires hardware support (EX/FX line cards on all spines) and is primarily needed for Nexus Dashboard Insights latency measurements. Enabling PTP without the prerequisite hardware would cause configuration errors, while enabling it unnecessarily adds operational complexity with no immediate benefit.
</tip>
<br><br>




## Port Tracking



The Port Tracking policy monitors the status of links between Leaf switches and Spine switches. When an enabled Port Tracking policy is triggered (the required number of Fabric uplink ports go down), the Leaf switch will shut down all of its access interfaces that have EPGs deployed on them.

The feature has two variables that can be adjusted as required:

- Delay restore timer - default 120 seconds (range 1 - 300 seconds) before the uplink is declared valid again, and the host ports are re-enabled.
- Number of active Spine links left that triggers port tracking - default 0 (range 0-12), meaning that the feature will only be triggered when zero Spine uplinks are forwarding (i.e., all uplinks have gone down).

Port tracking feature only disables in-service interfaces. The following ports are not disabled by this feature:

- Ports that have access policies but are 'out-of-service.'
- Ports connected to Spines.
- Ports connected to APICs (if not specifically selected).

This feature is especially relevant when hosts are connected using active/standby NIC teaming, or when specific access:Fabric port oversubscription ratios are required, however, it is anticipated that the majority of ACI-attached hosts need to be informed if the uplink ports of the Leaf switch are no longer forwarding traffic so they can take the appropriate action (e.g., failover their uplink).

The Port-Tracking feature addresses a scenario where a Leaf node may lose connectivity to all Spine nodes, however, its access ports remain enabled. This behavior can prevent the correct operation of host-based failover (e.g., active/standby or Port-Channels). The Port-Tracking feature detects a loss of Fabric connectivity on a Leaf node and brings down the host-facing ports, allowing the host to fail over to its second link.

<info name="Info">Port Tracking is not required on vPC ports. If all the Fabric links for the Leaf go down, then the vPC manager will automatically bring down all of its active vPCs. This action is taken to prevent a dual-active scenario.</info>

In the %%customerName ACI design, Port Tracking will be enabled with the default policy. APIC ports will be included because all APIC servers are dual-homed, connected to different leaf nodes.

<info name="Info">System / System Settings / Port Tracking.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the Port Tracking setting needs to be defined in the input files:

<caption name="Port Tracking Data Model">

```yaml
apic:
  fabric_policies:
    port_tracking:
      admin_state: true
      delay: 130
      min_links: 1
```
</caption>

For further information on how the Port Tracking setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/port_tracking/).



## System Performance



The system performance enables the configuration of the API response monitoring feature, which provides visibility into the REST API response time statistics.

A threshold time can be set beyond which requests are considered to be slow, as well as a calculation window during which the number of slow requests is calculated.

This feature creates an event for every APIC that has at least one request that exceeds the threshold within the calculation window. The event information includes the number of requests with the slowest response time within the event.

This feature is disabled by default. When enabled, the default response threshold is 85,000 msec, the default calculation window is 300 sec and the default number of slowest responses to be included in the event is 5.

In the %%customerName ACI design, the System Performance feature is initially disabled.

<info name="Info">System/System Settings/System Performance.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the System Performance setting is defined in the input files:

<caption name="System Performance Data Model">

```yaml
apic:
  fabric_policies:
    system_performance:
      admin_state: true
      response_threshold: 8500
      top_slowest_requests: 5
      calculation_window: 300
```
</caption>

For further info on how the System Performance setting is defined in the IaC data model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/system_performance/).



## System Global GIPo Policy



This feature is only relevant for ACI Multi-Pod environments.

By default, ACI Multi-Pod uses the 239.255.255.240/32 multicast address as the System Global IP outside (GIPo) address. The System GIPo range is used for ARP gleaning (to discover silent hosts in remote Pods) for all Bridge Domains that have ARP flooding disabled.

By enabling this feature, the System GIPo can use an address within the Infra GIPo (225.0.0.0/8 by default) range (used to allocate Multicast ranges to BDs), reducing the configuration required within the Multi-Pod Inter-Pod Network (IPN). With this feature disabled (default), both the 225.0.0.0/8 range and the 239.255.255.240/32 address must be configured as PIM BIDIR ranges on the IPN. This configuration can be avoided by using the Infra GIPo as the System GIPo. With this feature enabled, only the 225.0.0.0/8 is required.

Starting in release 4.0(1), this feature must be enabled for PBR tracking to function on a Remote Leaf network after a connection failure to parent Fabric.

In the %%customerName ACI design, the System Global GIPo Policy will be enabled to avoid configuring 239.255.255.240/32 as a PIM BIDIR range on the IPN.

<info name="Info">System / System Settings / System Global GIPo Policy.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the System Global GIPo Policy needs to be defined in the input files:

<caption name="System Global Gipo Policy Data Model">

```yaml
apic:
  fabric_policies:
    use_infra_gipo: true
```
</caption>

For further info on how the System Global GIPo Policy setting is defined in the IaC Data Model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/system_global_gipo/).



## System Alias and Banners



The GUI Alias allows a meaningful alias to be configured for the APIC.

The Controller and Switch Banners are text-based strings printed to the console as-is and display before the user login authentication.

<info name="Info">A banner is displayed to inform the user about security, legal information, and compliance.</info>

An Application Banner can be also configured to alert the user about outstanding issues, e.g., during a maintenance window when an upgrade is in progress.

<info name="Info">System/System Settings/System Alias and Banners.</info>

The IaC data model for ACI formally defines the format of the data input files. This is an example of how the System Alias and Banners are defined in the input files:

<caption name="System Alias And Banners Data Model">

```yaml
apic:
  fabric_policies:
    banners:
      apic_gui_alias: APIC GUI BANNER
      apic_gui_banner_url: APIC GUI BANNER URL
      apic_cli_banner: APIC CLI BANNER
      switch_cli_banner: SWITCH CLI BANNER
```
</caption>

For further info on how the System Alias and Banners is defined in the IaC data model for ACI, please refer to the [Network-as-Code (NaC) documentation](https://netascode.cisco.com/docs/data_models/apic/fabric_policies/banner/).



## BD Enforced Exception List



Cisco ACI supports the concept of 'enforced' BDs where endpoints are only able to ping the subnet gateway(s) of the BD to which their EPG is associated. This feature is particularly relevant where additional security is required to prevent end points from discovering other subnets to which they are not directly connected.

The BD Enforcement Status is configured at the VRF level and applies to all BDs associated with that VRF. The BD Enforced Exception List feature allows a global exception list of IP addresses (e.g., management endpoints) that are allowed to ping any subnet gateway in any VRF.

This feature only applies to VRFs that have 'BD Enforcement Status' enabled. The recommendation is for this feature not to be enabled unless there is a specific security requirement.

<info name="Info">System/System Settings/BD Enforced Exception List.</info>

In the %%customerName ACI design, initially, the use of the BD Enforcement Exception list will not be required.



## Quota



All ACI configuration is based on configuration units (e.g., BD, VRF, EPG, etc.), known as managed objects (MO). By defining a quota, the ACI administrator can limit the number of MOs that can be created globally or within a particular tenant. Quota definition has the following effects:

- Hardware resource protection - Configuration of some MOs requires hardware resources, which are finite by nature and must be protected. Assigning quotas prevents one tenant from consuming too many available resources and negatively impacting another tenant.
- Consumption policing - When ACI is deployed in a consumption-based model (e.g., customer X has only paid for one VRF, one L3Out and three Bridge Domains), this feature can be used to enforce these limits.

Quotas may be relevant in a multi-tenant environment, or when non-production tenants are operating on an ACI fabric carrying production traffic.

Quota configuration requires the following inputs:

- Class: the MO to be restricted, e.g., EPG, BD, VRF, L3Out.
- Container Dn: the parent distinguished name of the class, e.g., 'uni,' for a global quota to restrict for the whole fabric, or 'uni/tn-CustomerX' to restrict classes only within the tenant 'CustomerX.'
- Exceed Action: "Fail Transaction" or "Raise Fault" (but still permit the action).
- Max Number: quota limit.

In the %%customerName design, quotas will not be defined initially. However, should it be deemed necessary in the future, the following guidelines apply:

- The global limits are set to approximately 75% of the supported scalability limits for the particular software version (see [ACI Verified Scalability Guide](https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/verified-scalability/cisco-aci-verified-scalability-guide-601.html)), with an Exceed Action of 'Raise Fault,' to inform the administrator that the ACI scalability limits are close to being reached.

<info name="Info">System/System Settings/Quota.
</info>



## Remote Leaf Pod Redundancy Policy



This feature provides Pod Redundancy for Remote Leaf switches attached to a Multi-Pod Fabric. If a Remote Leaf switch loses connectivity to its Spine switch, then it is automatically connected to a Spine of another Pod.

<info name="Info">During Pod failover, there is an expected disruption to traffic of several seconds.</info>

If 'pre-emption' is enabled, the Remote Leaf switch is re-associated with the parent Pod once that Pod is back up. If 'pre-emption' is disabled, the Remote Leaf remains associated with the operational Pod even when the parent Pod comes back up.

<info name="Info">System / System Settings / Remote Leaf Pod Redundancy Policy.
</info>



## Customer ACI Fabric Configuration



%%customerName ACI fabric configuration

<caption name="ACI-FABRIC-NAME - %%customerName ACI fabric configuration">

| Setting | Parameter |
| --- | --- |
| System Response Time | N/A |
| Global AES Encryption Settings for all Configuration Import and Export | Not Configured |
| BD Enforced Exception List | N/A |
| Fabric Security | Configured |
| BGP Route Reflector | AS N/A |
| Control Plane MTU | N/A |
| COOP Group | compatible |
| Endpoint Control: | Endpoint Control: |
| EP Loop Protection | Disabled |
| Rogue EP Control: | Disabled |
| Detection interval | N/A seconds |
| Multiplication Factor | N/A |
| Hold interval | N/A seconds |
| IP Aging | Disabled |
| Fabric-Wide Settings: | Fabric-Wide Settings: |
| Disable Remote EP Learning | No |
| Enforce Subnet Check | No |
| Enforce EPG VLAN Validation | No |
| Reallocate GIPo | No |
| Enforce Domain Validation | No |
| Spine Opflex Client authentication | No |
| Leaf  Opflex Client authentication | No |
| Load Balancer | N/A |
| Port Tracking: | Disabled |
| Delay restore timer | N/A seconds |
| Number of active fabric ports that triggers port tracking | N/A |
| Include APIC ports when port tracking is triggered | No |
| Precision Time Protocol | Disabled |
| System Global GIPo Policy | Standard |

</caption>





# Appendix A: Acronyms



<caption name="Acronyms">

| Term | Definition |
|---|---|
| AAA | Authentication, Authorization and Accounting |
| ACI | Application Centric Infrastructure |
| ACL | Access-Control List |
| ACS | Access Control System |
| ADC | Application Delivery Controller |
| API | Application Programming Interface |
| APIC | Application Policy Infrastructure Controller |
| BFD | Bidirectional Forwarding Detection |
| BGP | Border Gateway Protocol |
| BOM | Bill of Materials |
| BPDU | Bridge Protocol Data Unit |
| DC | Data Center |
| DCI | Data Center Interconnect |
| DHCP | Dynamic Host Configuration Protocol |
| DMZ | Demilitarized Zone |
| DNS | Domain Name System |
| DR | Disaster Recovery |
| DWDM | Dense Wavelength Division Multiplexing |
| ECMP | Equal Cost Multi-Path |
| EoR | End of Row |
| EPG | Endpoint Group |
| ESXi | Vmware vSphere Hypervisor |
| FW | Firewall |
| Gbps | Gigabits per second |
| GE | Gigabit Ethernet |
| GSLB | Global Server Load Balancing |
| GUI | Graphical User Interface |
| HA | High Availability |
| HLD | High Level Design |
| HMAC | Hash-based Message Authentication Code |
| HSRP | Hot Standby Router Protocol |
| HTTP | Hypertext Transfer Protocol |
| HTTPS | Hypertext Transfer Protocol Secure |
| IaaS | Infrastructure as a Service |
| IaC | Infrastructure as Code |
| IEEE | Institute of Electrical and Electronics Engineers |
| IGP | Interior Gateway Protocol |
| IP | Internet Protocol |
| IPAM | IP Address Management |
| IPN | Inter-POD Network |
| IPS | Intrusion Prevention System |
| IPsec | Internet Protocol Security |
| IPSLA | IP Service Level Agreement |
| IPv4 | Internet Protocol version 4 |
| IPv6 | Internet Protocol version 6 |
| L2 | Layer 2 |
| L3 | Layer 3 |
| L4 | Layer 4 |
| L7 | Layer 7 |
| LACP | Link Aggregation Control Protocol |
| LB | Load Balancer |
| LC | Lucent Connector |
| LDP | Label Distribution Protocol |
| LEAF | Leaf switch in a Clos architecture |
| LLD | Low Level Design |
| LOM | Lights Out Management |
| MGMT | Management |
| MLAG | Multi-Chassis Link Aggregation Group |
| MMF | Multi-Mode Fiber |
| MP-BGP | Multi-Protocol Border Gateway Protocol |
| MPLS | Multi-Protocol Label Switching |
| MTU | Maximum Transmission Unit |
| NaC | Network as Code |
| ND | Nexus Dashboard |
| NDI | Nexus Dashboard Insights |
| NIC | Network Interface Card |
| NIP | Network Implementation Plan |
| NMP | Network Migration Plan |
| NMS | Network Management System |
| NRFU | Network Ready For Use |
| NTP | Network Time Protocol |
| OOB | Out of Band |
| OSPF | Open Shortest Path First |
| PBR | Policy Based Routing |
| PDU | Power Distribution Unit |
| QoS | Quality of Service |
| RBAC | Role Based Access Control |
| REST API | Representational State Transfer Application Programming Interface |
| RTT | Round Trip Time |
| RU | Rack Unit |
| SDD | Solution Design Document |
| SDDC | Software Defined Data Centre |
| SDN | Software Defined Networking |
| SFP | Small Form-Factor Pluggable |
| SLB | Server Load Balancer |
| SMF | Single Mode Fiber |
| SMTP | Simple Mail Transfer Protocol |
| SNMP | Simple Network Management Protocol |
| SPAN | Switched Port Analyzer |
| SPINE | Spine switch in a Clos architecture |
| SRD | Solution Requirements Document |
| SSH | Secure Shell |
| SSL | Secure Sockets Layer |
| TACACS | Terminal Access Controller Access-Control System |
| TCP | Transmission Control Protocol |
| TEP | Tunnel End Point |
| Terrafrom | Infrastructure as Code tool |
| VDS | Virtual Distributed Switch |
| VIP | Virtual IP |
| VLAN | Virtual Local Area Network |
| vLB | Virtual Load Balancer |
| VM | Virtual Machine |
| VMM | Virtual Machine Manager |
| vPC | Virtual Port Channel |
| VTEP | Virtual Tunnel End Point |
| VxLAN | Virtual Extensible Local Area Network |
| WAN | Wide Area Network |
| WDM | Wavelength Division Multiplexing |
| XML | Extensible Markup Language |
| ZTP | Zero Touch Provisioning |
</caption>



