// @mount /api/categories (public) + /api/admin/categories (admin)
const express = require('express');
const { authenticate, hasRole } = require('../middleware/auth');
const controller = require('../controllers/categoryController');

const publicRouter = express.Router();
const adminRouter = express.Router();

// ---- Public ----
publicRouter.get('/', controller.getCategoryTree);

// ---- Admin ----
adminRouter.get('/',     authenticate, hasRole('admin'), controller.adminGetCategoryTree);
adminRouter.post('/',    authenticate, hasRole('admin'), controller.createCategory);
adminRouter.put('/:id',  authenticate, hasRole('admin'), controller.updateCategory);
adminRouter.delete('/:id', authenticate, hasRole('admin'), controller.deleteCategory);

module.exports = { publicRouter, adminRouter };
