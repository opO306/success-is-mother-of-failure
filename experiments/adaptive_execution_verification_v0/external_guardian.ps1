# Administrative Vast control only. No tests, physics, GPU or server creation/start.
# Runs outside the guest; its fixed deadline survives guest/SSH/job termination.
param(
    [Parameter(Mandatory=$true)][int]$InstanceId,
    [Parameter(Mandatory=$true)][string]$Authorization,
    [Parameter(Mandatory=$true)][string]$Receipt,
    [ValidateRange(1,600)][int]$DeadlineSeconds = 15,
    [string]$CompletionMarker = ''
)
$ErrorActionPreference = 'Stop'
$lease = Get-Content -LiteralPath $Authorization -Raw | ConvertFrom-Json
if ($lease.scope -ne 'STOP_CONTROL_ONLY' -or $lease.explicit_user_approval -ne $true -or
    $lease.exclusive -ne $true -or [int]$lease.instance_id -ne $InstanceId -or
    [string]::IsNullOrWhiteSpace($lease.approval_reference)) { throw 'REFUSED_EXCLUSIVE_CONTROL_LEASE' }
if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLower() -ne $lease.guardian_sha256) {
    throw 'REFUSED_GUARDIAN_SEAL'
}
if (Test-Path -LiteralPath $Receipt) { throw 'REFUSED_EXISTING_RECEIPT' }
if ($CompletionMarker -and $lease.completion_marker -ne $CompletionMarker) { throw 'REFUSED_COMPLETION_MARKER' }
$cli = (Get-Command vastai -ErrorAction Stop).Source
$events = [Collections.Generic.List[object]]::new()
$trigger = 'DEADLINE'
$receiptDirectory = Split-Path -Parent $Receipt
[IO.Directory]::CreateDirectory($receiptDirectory) | Out-Null

function Save-ControlReceipt([string]$State) {
    $record = [ordered]@{
        schema='aev0-external-stop-control'; instance_id=$InstanceId; status=$State;
        trigger=$trigger; outside_guest=$true; local_numerical_execution=$false;
        guardian_sha256=$lease.guardian_sha256; approval_reference=$lease.approval_reference;
        events=@($events.ToArray()); observed_at_utc=[DateTime]::UtcNow.ToString('o')
    }
    $json = ($record | ConvertTo-Json -Depth 8) + [Environment]::NewLine
    # Only this guardian writes this receipt, first publication is exclusive.
    $mode = if (Test-Path -LiteralPath $Receipt) { [IO.FileMode]::Truncate } else { [IO.FileMode]::CreateNew }
    $stream = [IO.File]::Open($Receipt,$mode,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $data=[Text.UTF8Encoding]::new($false).GetBytes($json); $stream.Write($data,0,$data.Length) }
    finally { $stream.Dispose() }
}

function Invoke-VastControl([string[]]$Arguments, [bool]$RequireJson = $true) {
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName=$cli; $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    foreach ($item in (@('--raw','--retry','1') + $Arguments)) { $start.ArgumentList.Add($item) }
    $process=[Diagnostics.Process]::new(); $process.StartInfo=$start
    try {
        [void]$process.Start()
        $stdout=$process.StandardOutput.ReadToEndAsync(); $stderr=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(12000)) { $process.Kill(); throw 'CONTROL_REQUEST_TIMEOUT' }
        if ($process.ExitCode -ne 0) { throw 'CONTROL_CLI_FAILED' }
        $payload=$stdout.GetAwaiter().GetResult()
        [void]$stderr.GetAwaiter().GetResult()  # Never log credential-bearing CLI diagnostics.
        if (-not $RequireJson) { return [ordered]@{cli_exit=0; accepted_response_format='CLI_TEXT_OR_JSON'} }
        return ($payload | ConvertFrom-Json)
    } finally { $process.Dispose() }
}

try {
    $initial=Invoke-VastControl @('show','instance',"$InstanceId")
    if ([int]$initial.id -ne $InstanceId) { throw 'INSTANCE_ID_MISMATCH' }
    if ([double]$initial.dph_total -gt 0.25) { throw 'HOURLY_BUDGET_EXCEEDED' }
    $events.Add([ordered]@{event='ARMED'; actual_status=$initial.actual_status;
                              intended_status=$initial.intended_status; dph_total=$initial.dph_total;
                              at_utc=[DateTime]::UtcNow.ToString('o')})
    Save-ControlReceipt 'ARMED'
    $deadline=[DateTime]::UtcNow.AddSeconds($DeadlineSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($CompletionMarker -and (Test-Path -LiteralPath $CompletionMarker)) {
            $completion=Get-Content -LiteralPath $CompletionMarker -Raw | ConvertFrom-Json
            if ($completion.trigger -notin @('COMPLETED','FAILED')) { throw 'INVALID_COMPLETION_MARKER' }
            $trigger=$completion.trigger
            break
        }
        Start-Sleep -Seconds 1
    }
    for ($attempt=0; $attempt -lt 3; $attempt++) {
        try {
            $stop=Invoke-VastControl -Arguments @('stop','instance',"$InstanceId") -RequireJson $false
            $events.Add([ordered]@{event='STOP_REQUEST'; attempt=$attempt; cli_exit=$stop.cli_exit;
                                      at_utc=[DateTime]::UtcNow.ToString('o')})
        } catch { $events.Add([ordered]@{event='STOP_REQUEST_ERROR'; attempt=$attempt; error_type=$_.Exception.GetType().Name}) }
        for ($poll=0; $poll -lt 2; $poll++) {
            Start-Sleep -Seconds 2
            try {
                $current=Invoke-VastControl @('show','instance',"$InstanceId")
                if ([int]$current.id -ne $InstanceId) { throw 'INSTANCE_ID_MISMATCH' }
                $events.Add([ordered]@{event='STATE_OBSERVED'; actual_status=$current.actual_status;
                                          intended_status=$current.intended_status; at_utc=[DateTime]::UtcNow.ToString('o')})
                if ($current.actual_status -in @('stopped','exited')) {
                    Save-ControlReceipt 'STOP_CONFIRMED'; exit 0
                }
            } catch { $events.Add([ordered]@{event='STATE_READ_ERROR'; error_type=$_.Exception.GetType().Name}) }
        }
        Save-ControlReceipt 'STOP_PENDING'
    }
    Save-ControlReceipt 'STOP_UNCONFIRMED'; exit 2
} catch {
    $events.Add([ordered]@{event='CONTROL_FAILURE'; error_type=$_.Exception.GetType().Name})
    Save-ControlReceipt 'CONTROL_FAILURE'; exit 3
}
