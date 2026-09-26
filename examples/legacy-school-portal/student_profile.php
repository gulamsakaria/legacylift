<?php
/**
 * Student profile loader — restores a saved preferences object from the
 * query string so the page can remember column visibility, sort order, etc.
 *
 * NOTE: This is intentionally insecure legacy code used as a demo fixture
 * for LegacyLift's LL015 (PHP object injection) detection rule.
 */

require_once __DIR__ . '/includes/bootstrap.php';

// Restore the user's saved preferences from the URL parameter.
// VULNERABLE: unserialize() on attacker-controlled request input allows
// PHP Object Injection — an attacker can craft a serialized payload that
// triggers arbitrary __wakeup() / __destruct() magic-method chains.
if (isset($_GET['prefs'])) {
    $prefs = unserialize($_GET['prefs']);
} else {
    $prefs = ['sort' => 'name', 'cols' => 'all'];
}

// Also accept overrides posted from the preferences form.
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['prefs_data'])) {
    // VULNERABLE: same pattern via $_POST
    $posted_prefs = unserialize($_POST['prefs_data']);
    if (is_array($posted_prefs)) {
        $prefs = array_merge($prefs, $posted_prefs);
    }
}

$student_id = intval($_GET['id'] ?? 0);
$sql = "SELECT * FROM students WHERE id = $student_id";
$result = mysql_query($sql);
$student = mysql_fetch_assoc($result);
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Student Profile</title></head>
<body>
<h1>Student Profile</h1>
<?php if ($student): ?>
  <p><strong>Name:</strong> <?= $student['name'] ?></p>
  <p><strong>Email:</strong> <?= $student['email'] ?></p>
  <p><strong>Sort preference:</strong> <?= $prefs['sort'] ?></p>
<?php else: ?>
  <p>Student not found.</p>
<?php endif; ?>

<form method="post">
  <input type="hidden" name="prefs_data" value="<?= htmlspecialchars(serialize($prefs)) ?>">
  <button type="submit">Save preferences</button>
</form>
</body>
</html>
