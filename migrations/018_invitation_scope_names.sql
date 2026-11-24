-- Display names are invitation metadata. Permission checks still use the
-- immutable composite scope keys. Populate labels only for outstanding offers.
ALTER TABLE portal_invitations ADD COLUMN brand_name varchar(160), ADD COLUMN campaign_name varchar(160);
UPDATE portal_invitations i SET brand_name=b.name FROM brands b
 WHERE i.state='pending' AND (b.tenant_id,b.client_id,b.id)=(i.tenant_id,i.client_id,i.brand_id);
UPDATE portal_invitations i SET campaign_name=c.name FROM campaigns c
 WHERE i.state='pending' AND (c.tenant_id,c.brand_id,c.id)=(i.tenant_id,i.brand_id,i.campaign_id);
