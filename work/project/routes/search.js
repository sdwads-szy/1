// @mount /api/search
const express = require('express');
const router = express.Router();
const { optionalAuth } = require('../middleware/auth');
const searchController = require('../controllers/searchController');

router.get('/', optionalAuth, searchController.search);
router.get('/suggestions', optionalAuth, searchController.suggestions);

module.exports = router;
