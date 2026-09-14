<?php
// This file is part of Moodle - http://moodle.org/

require_once(__DIR__ . '/../../config.php');
require_once(__DIR__ . '/classes/prediction_reader.php');

require_login();
require_sesskey();

$predictionid = optional_param('prediction_id', '', PARAM_TEXT);
$studentkey = required_param('student_key', PARAM_TEXT);
$coursekey = optional_param('course_key', '', PARAM_TEXT);
$snapshotdate = optional_param('snapshot_date', '', PARAM_TEXT);
$ucrisklevel = required_param('uc_risk_level', PARAM_ALPHA);
$ucagreement = required_param('uc_agreement', PARAM_ALPHA);
$feedbackreasons = optional_param_array('feedback_reason', [], PARAM_TEXT);
$interventionstatus = required_param('intervention_status', PARAM_ALPHA);
$comments = optional_param('comments', '', PARAM_RAW_TRIMMED);

$risklevels = ['High', 'Moderate', 'Low'];
$agreements = ['Agree', 'Disagree', 'Unsure'];
$interventionstatuses = ['Yes', 'Planned', 'No'];
$allowedreasons = [
    'Academic performance concern',
    'Behaviour or engagement concern',
    'Attendance or participation concern',
    'Known personal or wellbeing context',
    'Moodle data may be incomplete',
    'Other',
];

$allowedcoursekeys = \block_smartlmsdashboard\prediction_reader::get_allowed_course_keys();
if ($allowedcoursekeys !== null && !in_array((string)$coursekey, array_map('strval', $allowedcoursekeys), true)) {
    throw new required_capability_exception(context_system::instance(), 'block/smartlmsdashboard:view', 'nopermissions', '');
}
if ($allowedcoursekeys === [] && !\block_smartlmsdashboard\prediction_reader::user_can_view_all_units()) {
    throw new required_capability_exception(context_system::instance(), 'block/smartlmsdashboard:view', 'nopermissions', '');
}

if (!in_array($ucrisklevel, $risklevels, true)) {
    throw new moodle_exception('Invalid UC risk level.');
}
if (!in_array($ucagreement, $agreements, true)) {
    throw new moodle_exception('Invalid agreement value.');
}
if (!in_array($interventionstatus, $interventionstatuses, true)) {
    throw new moodle_exception('Invalid intervention status.');
}

$feedbackreasons = array_values(array_intersect($feedbackreasons, $allowedreasons));

$feedbackid = gmdate('YmdHis') . '-' . bin2hex(random_bytes(4));
$reviewedby = fullname($USER) . ' (id:' . $USER->id . ')';
$reviewedat = gmdate('c');
$feedbackreasontext = implode('; ', $feedbackreasons);

$DB->execute("
    CREATE TABLE IF NOT EXISTS ml_db.prediction_feedback (
        feedback_id VARCHAR(40) NOT NULL PRIMARY KEY,
        prediction_id VARCHAR(100) NULL,
        student_key VARCHAR(100) NOT NULL,
        course_key VARCHAR(100) NULL,
        snapshot_date VARCHAR(50) NULL,
        uc_risk_level VARCHAR(20) NOT NULL,
        uc_agreement VARCHAR(20) NOT NULL,
        feedback_reason TEXT NULL,
        intervention_status VARCHAR(20) NOT NULL,
        comments TEXT NULL,
        reviewed_by VARCHAR(255) NOT NULL,
        reviewed_at VARCHAR(40) NOT NULL
    )
");

$DB->execute("
    INSERT INTO ml_db.prediction_feedback (
        feedback_id,
        prediction_id,
        student_key,
        course_key,
        snapshot_date,
        uc_risk_level,
        uc_agreement,
        feedback_reason,
        intervention_status,
        comments,
        reviewed_by,
        reviewed_at
    ) VALUES (
        :feedback_id,
        :prediction_id,
        :student_key,
        :course_key,
        :snapshot_date,
        :uc_risk_level,
        :uc_agreement,
        :feedback_reason,
        :intervention_status,
        :comments,
        :reviewed_by,
        :reviewed_at
    )
", [
    'feedback_id' => $feedbackid,
    'prediction_id' => $predictionid,
    'student_key' => $studentkey,
    'course_key' => $coursekey,
    'snapshot_date' => $snapshotdate,
    'uc_risk_level' => $ucrisklevel,
    'uc_agreement' => $ucagreement,
    'feedback_reason' => $feedbackreasontext,
    'intervention_status' => $interventionstatus,
    'comments' => $comments,
    'reviewed_by' => $reviewedby,
    'reviewed_at' => $reviewedat,
]);

header('Content-Type: application/json');
echo json_encode([
    'success' => true,
    'feedback_id' => $feedbackid,
]);
