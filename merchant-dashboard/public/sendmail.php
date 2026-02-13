<?php

/* INTERNAL FIELDS - ContactForm/view/index */
/* Convert to const */
$internalFields = array(
    "cmpId", "replyto", "subject",  "recipient", "email", "formLabels", "formLabelsTypeMappings",
);

define("FRIENDLY_CAPTCHA_FIELDS", array("frc-captcha-solution", "frc-captcha-version"));

// Convert string to lower case
function toLower ($str) {
    return strtolower($str);
}

/**
 * This function converts punycode domain in email address to ascii.
 * This is required for string comparison and regex validation of email.
 *
 * @param string    $email
 *
 * @return string
 */
function emailToASCII ($email) {
    $parts = explode("@", $email);

    if (count($parts) === 2) {
        list($username, $domain) = $parts;

        $asciiDomain = $domain;

        if (function_exists("idn_to_ascii")) {
            // See https://www.php.net/idn_to_ascii
            $asciiDomain = idn_to_ascii($domain, IDNA_DEFAULT, INTL_IDNA_VARIANT_UTS46);
            if ($asciiDomain === false) {
                $asciiDomain = $domain;
            }
        }

        return ($username . "@" . $asciiDomain);
    }

    // Should never be the case
    return $email;
}

/**
 * Validate for email. Since domain names can have punycode characters, its necessary to convert
 * them to ASCII before running through regex validation.
 *
 * @param string $value
 *
 * @return boolean
 */
function isValidEmail($email, $toASCII = true) {
    $asciiEmail = $toASCII ? emailToASCII($email) : $email;
    // See https://www.php.net/filter_var
    return filter_var($asciiEmail, FILTER_VALIDATE_EMAIL);
}

/**
 * Get UTF-8 encoded value
 *
 * @param string $value
 *
 * @return string UTF-8 encoded value
 */
function getUtf8Encoded($value) {
    return "=?UTF-8?B?" . base64_encode($value) . "?=";
}

/**
 * Detect the replyto email from HTTP POST
 * 
 * @return string The reply-to email from the HTTP POST
 */
function getReplyToEmailFromHttpPost() {
    global $internalFields;

    // Some customers may not have email field in the contact form
    $replyToEmail = isset($_POST["replyto"]) ? trim($_POST["replyto"]) : "";

    if (empty($replyToEmail)) {
        foreach ($_POST as $field => $value) {
            if (!in_array($field, $internalFields) && !empty($value) && isValidEmail($value)) {
                $replyToEmail = $value;
                break;
            }
        }
    }

    return $replyToEmail;
}

function getRealLabel ($field) {
    if (!empty($_POST["formLabels"])) {
        $arrFormLabels = explode("====", $_POST["formLabels"]);

        $mapFormLabels = array_reduce(
            $arrFormLabels,
            function ($acc, $label) {
                // To match the labels converted by PHP engine
                $newLabel = preg_replace("/[\s\.]/", "_", preg_replace("/^\s+/", "", $label));
                $acc[$newLabel] = $label;
                return $acc;
            },
            []
        );

        return $mapFormLabels[$field] ?: $field;
    }

    return $field;
}

/**
 * Returns the text to be prepended for the message
 *
 * @param   $replyTo            string  The email filled by the website user
 *
 * @return  string
 */
function getTopText ($replyTo) {
    $message = "You received a new message sent via the contact form on apiblockchain.io.";
    $message = strlen($message) > 0 ? $message : "You received a new message from __REPLYTO__ sent via the contact form on apiblockchain.io.";
    $message = str_replace("__REPLYTO__", $replyTo, $message);

    return "<p>" . $message . "</p>" . "<br />" . "\r\n";
}

/**
 * Returns the message to be sent
 *
 * @param   $replyTo            string  The email filled by the website user
 * @param   $boundary           string  The mail message boundary string
 * @param   $skipFieldIfEmpty   boolean Flag to determine if empty form fields should be skipped from message
 *
 * @return string
 */
function getMessageToSend ($replyTo, $boundary, $skipFieldIfEmpty = true) {
    global $internalFields;

    $arrMessage = array();

    foreach($_POST as $field => $value) {
        if (
            in_array($field, $internalFields) ||                // Skip internal fields
            in_array(toLower($field), FRIENDLY_CAPTCHA_FIELDS)  // Skip friendly captcha fields
        ) {
            // Just skip
        } else if ($skipFieldIfEmpty && (!isset($value) || empty($value))) {
            // Do nothing
        } else {
            $realField = htmlspecialchars(ucfirst(getRealLabel(rawurldecode($field))));
            $realValue = nl2br(htmlspecialchars($value));

            array_push($arrMessage, array($realField, $realValue));
        }
    }

    // In case Marketing consent is part of $_POST, it should be the last field in the mail being composed.
    $keys = array_keys(
        array_filter(
            $arrMessage,
            function ($row) {
                return preg_match("/Marketing Consent/", $row[0]);
            }
        )
    );

    if(count($keys) > 0) {
        $marketingConsent = array_splice($arrMessage, $keys[0], 1);
        array_push($arrMessage, $marketingConsent[0]);
    }

    $message = "--$boundary\r\n";
    $message .= "Content-Type: text/html; charset=UTF-8\r\n";
    $message .= "Content-Transfer-Encoding: base64\r\n\r\n";

    $topText = getTopText($replyTo);
    $message .= chunk_split(base64_encode(getMessageHTML($topText, $arrMessage)));

    return $message;
}

function getMessageHTML($topText, $arrMessage) {
    return (
        "<html>" .
            "<head>" .
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">" .
            "</head>" .
            "<body>" .
                "<p>" . $topText . "</p>" .
                getMessageHTMLContent($arrMessage) .
            "</body>" .
        "</html>"
    );
}

function getValueByType ($field, $value) {
    $hrefType = "";
    $formLabelsTypeMappings = json_decode($_POST["formLabelsTypeMappings"], true);

    if (isset($formLabelsTypeMappings)) {
        $fieldType = isset($formLabelsTypeMappings[$field]) ? $formLabelsTypeMappings[$field] : "";

        if ($fieldType === "email") {
            $hrefType = "mailto:";
        } else if ($fieldType === "phone") {
            $hrefType = "tel:";
        } else if ($fieldType === "url") {
            $hrefType = "https://";
            preg_match("/^https?:\/\//", $value, $matches);
            if (is_array($matches) && count($matches) > 0) {
                $hrefType = $matches[0];
                $value = str_replace($hrefType, "", $value);
            }
        }
    }

    $value = strip_tags($value);

    return strlen($hrefType) > 0
        ? ("<a href=\"" . $hrefType . $value . "\">" . $value .  "</a>")
        : $value;
}

function getMessageHTMLContent ($arrMessage) {
    $shouldWrap = false;

    $maxLength = 60;

    foreach($arrMessage as $row) {
        list($field, $value) = $row;
        $shouldWrap = strlen($field) > $maxLength || strlen($value) > $maxLength;
        if ($shouldWrap === true) {
            break;
        }
    }

    function wrapContents($row, $shouldWrap = false) {
        list($field, $value) = $row;

        $displayValue = getValueByType($field, $value);

        if ($shouldWrap === true) {
            return (
                "<tr style=\" margin: 4px;\">" .
                    "<td style=\"margin: 0 4px 0; min-width: 135px; font-weight: bolder;\">" . $field . ": </td>" .
                "</tr>" .
                "<tr style=\"margin: 4px;\">" .
                    "<td style=\"margin: 0 4px 0;\"> " . $displayValue . " </td>" .
                "</tr>"
            );
        } else {
            return (
                "<tr style=\"margin: 4px;\">" .
                    "<td style=\"margin: 0 4px 0; min-width: 135px; font-weight: bolder;\">" . $field . ": </td>" .
                    "<td style=\"margin: 0 4px 0;\"> " . $displayValue . " </td>" .
                "</tr>"
            );
        }
    }

    return (
        "<table role=\"presentation\">" .
            "<tbody>" .
            implode("", array_map(function ($row) use ($shouldWrap) {
                return wrapContents($row, $shouldWrap);
            }, $arrMessage)) .
            "</tbody>" . 
        "</table>"
    );
}

/**
 * Validate the HTTP request method
 *
 * @param   $requestMethod  string  The HTTP request method
 *
 * @return boolean
 */
function validateRequestMethod($requestMethod) {
    return "POST" === strtoupper($requestMethod);
}

/**
 * Validate the requester
 *
 * @return boolean
 */
function isValidRequester() {
    $apacheHeaders = apache_request_headers();

    $appId  = $apacheHeaders['X-Appid'] ?: "";
    $appIds = json_decode('["oneConnectFormmail"]');

    return (
        !empty($appId) &&
        is_array($appIds) &&
        in_array($appId, $appIds, true)
    );
}

/**
 * Converts attacments as message body with appropriate message boundary
 *
 * @param   $boundary   string  The mail message boundary string
 *
 * @return string
 */
function getAttachmentsAsMessage ($boundary) {
    $attachmentMessage = "\r\n";

    if (!empty($_FILES)) {
        foreach ($_FILES as $file) {
            if ($file['error'] == UPLOAD_ERR_OK) {
                $fileContent = file_get_contents($file['tmp_name']);
                $fileName = $file['name'];
                $fileType = $file['type'];

                $attachmentMessage .= "--{$boundary}\r\n";
                $attachmentMessage .= "Content-Type: {$fileType}; name=\"{$fileName}\"\r\n";
                $attachmentMessage .= "Content-Disposition: attachment; filename=\"{$fileName}\"\r\n";
                $attachmentMessage .= "Content-Transfer-Encoding: base64\r\n\r\n";
                $attachmentMessage .= chunk_split(base64_encode($fileContent)) . "\r\n";
            }
        }
    }
    
    $attachmentMessage .= "--$boundary--";

    return $attachmentMessage;
}

/**
 * Generate the required headers
 *
 * @param   $from       string  The from email id
 * @param   $replyTo    string  The reply to email id
 * @param   $boundary   string  The mail message boundary string
 *
 * @return string
 */
function getMailHeaders ($from, $replyTo, $boundary) {
    $headers = array(
        "From: $from",
        "Reply-To: $replyTo",
        "MIME-Version: 1.0",
        implode(" ", array("Content-Type: multipart/mixed; boundary=\"$boundary\"")),
        "Message-ID: <" . implode("@", [md5(uniqid(time())), "apiblockchain.io"]) . ">",
        "Date: ".date("r (T)"),
        "X_Mailer: PHP/" . phpversion(),
        "X-G1i-WSB-Sendmail: 128.0.30",
    );

    return implode("\r\n", $headers);
}

function getDebugInfo() {
    $debugInfo = "";

    $debugHeader = isset($_SERVER['X-Mail-Debug']) ?: "";

    if (isValidRequester() || $debugHeader === "apiblockchain.io") {
        $lastError = error_get_last();

        $debugInfo= $lastError && is_array($lastError)
            ? ("Message: " . $lastError["message"] . " Line: " . $lastError["line"])
            : "Could not get last error";
    }

    return $debugInfo;
}

/**
 * Handle the mail sending along with validation 
 */
function processMail() {
    $response = array();

    $httpResponseCode = 200;

    // Validations
    if (!isValidRequester()) {
        $response['success'] = false;
        $response['error'] = 'HTTP referer mismatch';
    }

    if (empty($response)) {
        $requestMethod = $_SERVER['REQUEST_METHOD'] ?: null;
        if (!validateRequestMethod($requestMethod)) {
            $response['success'] = false;
            $response['error'] = 'HTTP request method mismatch';
        }
    }

    if (empty($response)) {
        $contactFormEmails = json_decode('{"5EC741B1-9364-4F05-B7C3-4D266DC0B302":"info@apiblockchain.io"}', true);

        $cmpId = $_POST['cmpId'];   // Contact form identifier to match recipient email
        if (!isset($cmpId) || !array_key_exists($cmpId, $contactFormEmails)) {
            $response['success'] = false;
            $response['error'] = 'Contact form identifier missing in request body';
        }

        if (empty($response)) {
            $recipient = $contactFormEmails[$cmpId];
            $from = "" ?: $recipient;

            $replyTo = getReplyToEmailFromHttpPost();
            if (empty($replyTo)) {
                $replyTo = $from;
            }

            // NOTE: Boundary should be used only for multipart
            $boundary = md5(time());

            // Get Headers
            $headers = getMailHeaders($from, $replyTo, $boundary);

            // Get subject
            $subject = getUtf8Encoded($_POST['subject']);

            // Get message body with attachments
            $message = "";

            $message .= getMessageToSend($replyTo, $boundary);
            $message .= getAttachmentsAsMessage($boundary);

            $additionalParamAllowed = strtolower("no");

            if (toLower($additionalParamAllowed) === "yes") {
                $additional_params = "-f " . $from;
                $success = mail($recipient, $subject, $message, $headers, $additional_params);
            } else {
                $success = mail($recipient, $subject, $message, $headers);
            }

            $response['recipient'] = $recipient;
            $response['success'] = $success;
            $response['error'] = "";

            if (!$success) {
                $httpResponseCode  = 500;
                $response['error'] = "Error sending mail";

                $debugInfo = getDebugInfo();
                if (!empty($debugInfo)) {
                    $response['debug'] = $debugInfo;
                }
            }
        }
    }

    // Set the HTTP header and JSON response
    header('Content-type: application/json', true, $httpResponseCode);
    echo json_encode($response);
}

processMail();

?>
