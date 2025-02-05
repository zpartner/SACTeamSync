token_url 	= 	Token_url 	( look in Administration -> App Integration )  

crsf_url 	= 	Tenant_url    	/api/v1/csrf  

users_url 	= 	Tenant_url 	/api/v1/scim2/Users  

crsf_url 	= 	Tenant_url	/api/v1/csrf  

groups_url	=	Tenant_url	/api/v1/scim2/Groups?count=100&filter=displayName ne \"StructuredAllocationRole_Admin\""  ( ONLY Source Tenant )  

                   ( Currently only 100 Teams will be fetched, if you have more please adjust. The exclustion of the Group “StructuredAllocationRole_Admin” is needed because of an SAP Bug.)  

client_id 	=	Oauth Client ID  

client_secret	=	Oauth Client Secret  

groups_post_url =  Tenant_url   	/api/v1/scim2/Groups ( ONLY Target Tenant )
