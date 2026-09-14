<?php
// This file is part of Moodle - http://moodle.org/

require_once(__DIR__ . '/../../config.php');
require_once(__DIR__ . '/classes/prediction_reader.php');

require_login();
require_sesskey();

$coursekey = required_param('course_key', PARAM_TEXT);
$courselabel = optional_param('course_label', '', PARAM_TEXT);
$teachingmode = required_param('teaching_mode', PARAM_TEXT);
$riskthreshold = required_param('risk_threshold', PARAM_FLOAT);
$notificationfrequency = required_param('notification_frequency', PARAM_TEXT);

$notifyweek1 = optional_param('notify_week1_no_activity', 0, PARAM_BOOL);
$notifyweek2 = optional_param('notify_week2_no_activity', 0, PARAM_BOOL);
$notifyweek3 = optional_param('notify_week3_no_activity', 0, PARAM_BOOL);
$notifynewhighrisk = optional_param('notify_new_high_risk', 0, PARAM_BOOL);
$notifynolmsactivity = optional_param('notify_no_lms_activity', 0, PARAM_BOOL);

$teachingmodes = ['High', 'Medium', 'Low'];
$frequencies = ['Immediately', 'Weekly summary', 'End of teaching week'];

if (!in_array($teachingmode, $teachingmodes, true)) {
    throw new moodle_exception('Invalid teaching mode.');
}
if (!in_array($notificationfrequency, $frequencies, true)) {
    throw new moodle_exception('Invalid notification frequency.');
}
if ($riskthreshold < 0 || $riskthreshold > 1) {
    throw new moodle_exception('Risk threshold must be between 0 and 1.');
}
$allowedcoursekeys = \block_smartlmsdashboard\prediction_reader::get_allowed_course_keys();
if ($allowedcoursekeys !== null && !in_array((string)$coursekey, array_map('strval', $allowedcoursekeys), true)) {
    throw new required_capability_exception(context_system::instance(), 'block/smartlmsdashboard:view', 'nopermissions', '');
}
if ($allowedcoursekeys === [] && !\block_smartlmsdashboard\prediction_reader::user_can_view_all_units()) {
    throw new required_capability_exception(context_system::instance(), 'block/smartlmsdashboard:view', 'nopermissions', '');
}

$now = time();
$record = (object)[
    'course_key' => $coursekey,
    'course_label' => $courselabel,
    'userid' => $USER->id,
    'teaching_mode' => $teachingmode,
    'notify_week1_no_activity' => $notifyweek1 ? 1 : 0,
    'notify_week2_no_activity' => $notifyweek2 ? 1 : 0,
    'notify_week3_no_activity' => $notifyweek3 ? 1 : 0,
    'risk_threshold' => round($riskthreshold, 2),
    'notify_new_high_risk' => $notifynewhighrisk ? 1 : 0,
    'notify_no_lms_activity' => $notifynolmsactivity ? 1 : 0,
    'notification_frequency' => $notificationfrequency,
    'timemodified' => $now,
];

$existing = $DB->get_record('block_smartlms_course_config', [
    'course_key' => $coursekey,
    'userid' => $USER->id,
]);

if ($existing) {
    $record->id = $existing->id;
    $DB->update_record('block_smartlms_course_config', $record);
    $id = $existing->id;
} else {
    $record->timecreated = $now;
    $id = $DB->insert_record('block_smartlms_course_config', $record);
}

header('Content-Type: application/json');
echo json_encode([
    'success' => true,
    'id' => $id,
    'config' => [
        'courseKey' => $coursekey,
        'courseLabel' => $courselabel,
        'teachingMode' => $teachingmode,
        'earlyEngagementNotifications' => [
            'week1' => (bool)$notifyweek1,
            'week2' => (bool)$notifyweek2,
            'week3' => (bool)$notifyweek3,
        ],
        'riskThreshold' => round($riskthreshold, 2),
        'notificationTypes' => [
            'newHighRisk' => (bool)$notifynewhighrisk,
            'noLmsActivity' => (bool)$notifynolmsactivity,
        ],
        'notificationFrequency' => $notificationfrequency,
        'isConfigured' => true,
    ],
]);
