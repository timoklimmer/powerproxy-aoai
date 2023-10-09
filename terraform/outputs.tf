output "ip_addresses" {
  value = azurerm_container_app.this.outbound_ip_addresses
}

output "fqdn" {
  value = azurerm_container_app.this.latest_revision_fqdn
}
