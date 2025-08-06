function Read-HostWithDefault($prompt, $default) {
    $input = Read-Host "$prompt [$default]"
    if ([string]::IsNullOrWhiteSpace($input)) {
        return $default
    } else {
        return $input
    }
}

# Get system UUID automatically
$uuid = (Get-WmiObject Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID).Trim()

# Get SerienNumber (BIOS serial number) automatically
$seriennumber = (Get-WmiObject Win32_BIOS | Select-Object -ExpandProperty SerialNumber).Trim()

# Prompt for other inputs
$hostname = Read-Host "Enter Hostname"
$mac = Read-Host "Enter MAC"
$ip = Read-Host "Enter IP"
$ticket = Read-Host "Enter Ticket"
# zentrum is first 4 letters of hostname (or less if hostname is shorter)
$zentrum = if ($hostname.Length -ge 4) { $hostname.Substring(0,4) } else { $hostname }
#$seriennumber = Read-Host "Enter SerienNumber"
$status = Read-HostWithDefault "Enter Status (LAGER, BETANKUNG, VERSENDET)" "LAGER"
$enduser = Read-Host "Enter Enduser"
$admin = Read-Host "Enter Admin"

# Build form data hashtable
$formData = @{
    hostname = $hostname
    mac = $mac
    ip = $ip
    ticket = $ticket
    uuid = $uuid
    zentrum = $zentrum
    seriennumber = $seriennumber
    status = $status.ToUpper()
    enduser = $enduser
    admin = $admin
}

# Encode form data
$formBodyParts = $formData.GetEnumerator() | ForEach-Object {
    [uri]::EscapeDataString($_.Key) + "=" + [uri]::EscapeDataString($_.Value)
}
$formBody = $formBodyParts -join "&"

# Send POST request
$response = Invoke-WebRequest -Uri "http://localhost:8000/add" `
    -Method POST `
    -Body $formBody `
    -ContentType "application/x-www-form-urlencoded"

if ($response.StatusCode -eq 303) {
    Write-Host "Entry added successfully!"
} else {
    Write-Host "Failed to add entry. Status code:" $response.StatusCode
    Write-Host "Response:" $response.Content
}


