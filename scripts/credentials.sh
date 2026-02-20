#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Avnet
# Authors: Nikola Markovic <nikola.markovic@avnet.com> and Zackary Andraka <zackary.andraka@avnet.com> et al.

set -e

# workaround for Git bash failing with subject formatting error for openssl
export MSYS_NO_PATHCONV=1

OUTDIR="/opt/demo"

function askyn {
    if [ -z "$1" ]; then
        echo "Need argument 1" >&2
        exit 128
    fi

    while true; do
        read -rp "$1 [y/n]: " answer
        if [[ "${answer}" =~ ^[yY]$ ]]; then
            return 0
        elif [[ "${answer}" =~ ^[nN]$ ]]; then
            return 1
        else
            echo "Please answer 'y' or 'n'."
        fi
    done
}

function gencert {
    if [ -z "$1" ]; then
        echo "Need argument 1" >&2
        exit 128
    fi

    cn=$1
    subj="/C=US/ST=IL/L=Chicago/O=IoTConnect/CN=${cn}"
    days=36500   # 100 years
    ec_curve=prime256v1

    openssl ecparam -name ${ec_curve} -genkey -noout \
        -out "${OUTDIR}/${cn}-pkey.pem"

    openssl req -new -days ${days} -nodes -x509 \
        -subj "${subj}" \
        -key "${OUTDIR}/${cn}-pkey.pem" \
        -out "${OUTDIR}/${cn}-cert.pem"

    echo "X509 credentials generated:"
    echo "  ${OUTDIR}/${cn}-cert.pem"
    echo "  ${OUTDIR}/${cn}-pkey.pem"
}

DEVICE_CERT="${OUTDIR}/device-cert.pem"
DEVICE_KEY="${OUTDIR}/device-pkey.pem"
generated_device_cert=false
reuse_existing_device_cert=false
print_device_cert=false

if [[ -f "${DEVICE_CERT}" && -f "${DEVICE_KEY}" ]]; then
    if askyn "Device certificate and key already exist. Regenerate?"; then
        gencert "device"
        generated_device_cert=true
        print_device_cert=true
    else
        echo "Keeping existing device certificate and key."
        reuse_existing_device_cert=true
        if ! askyn "Continue onboarding with existing credentials?"; then
            echo "Exiting without modifying device credentials."
            exit 0
        fi
        echo "Reusing existing credentials. Skipping certificate reprint."
    fi
else
    gencert "device"
    generated_device_cert=true
    print_device_cert=true
fi

if ${generated_device_cert}; then
    cert_action="generated"
else
    cert_action="existing"
fi

cat <<END
---- /IOTCONNECT Python Lite Certificate Script ----
This script will use and format ${cert_action} device credentials for your Arduino Uno Q
to help onboard it into /IOTCONNECT.
END

if ${print_device_cert}; then
    read -rp "ENTER to print the certificate and proceed:"
    cat "${DEVICE_CERT}"
fi

cat <<END
- Click the "Save & View" button.
- Click the "Paper and Cog" icon at top right to download your device configuration file.
END

CONFIG_JSON="${OUTDIR}/iotcDeviceConfig.json"
paste_config_json=false

if ${generated_device_cert}; then
    paste_config_json=true
fi

if ${reuse_existing_device_cert}; then
    if [[ -f "${CONFIG_JSON}" ]]; then
        echo "Keeping existing iotcDeviceConfig.json."
    else
        echo "iotcDeviceConfig.json not found. A config file is required to continue."
        paste_config_json=true
    fi
fi

if ${paste_config_json}; then
    if [[ -f "${CONFIG_JSON}" ]]; then
        if ! askyn "iotcDeviceConfig.json already exists. Overwrite?"; then
            echo "Keeping existing iotcDeviceConfig.json."
            paste_config_json=false
        fi
    fi
fi

if ${paste_config_json}; then
    echo "Paste the downloaded config file here and press ENTER after the last line:"
    > "${CONFIG_JSON}"

    while true; do
        read -r line
        echo "${line}" >> "${CONFIG_JSON}"
        if [[ "${line}" == "}" ]]; then
            break
        fi
    done
fi

cat <<END

The onboarding process is complete.

END
