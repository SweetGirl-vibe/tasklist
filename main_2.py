import sqlite3
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget,
                             QApplication,
                             QMessageBox,
                             QListWidgetItem,
                             QDialog,
                             QInputDialog)

from tasks import Ui_Form as tasksForm
from categories import Ui_Form as categoriesForm

DATABASE_NAME = 'tasks_db.db'


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def createTables(con):
    try:
        with con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE
                );
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                category_id INTEGER NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories (id) 
                ON DELETE CASCADE
                );
            """)
    except sqlite3.DatabaseError as e:
        print(f'{e.__class__.__name__}: {e}')
        sys.exit(-1)


class Categories(QDialog, categoriesForm):
    def __init__(self, con):
        super().__init__()
        self.setupUi(self)
        self.con = con
        self.loadCategories()
        self.addCategoryButton.clicked.connect(self.addCategory)
        self.deleteCategoryButton.clicked.connect(self.deleteCategory)

    def loadCategories(self):
        result = self.con.execute('''
            SELECT title FROM categories;
        ''').fetchall()
        self.categoriesList.clear()
        for i in result:
            self.categoriesList.addItem(i[0])

    def addCategory(self):
        text, ok = QInputDialog.getText(self, "Вы уверены?", "Введите имя категории:")
        if ok:
            with self.con:
                self.con.execute('''
                    INSERT INTO categories(title)
                    VALUES (?);
                ''', (text,))
                self.loadCategories()

    def deleteCategory(self):
        category = self.categoriesList.currentItem().text()
        result = QMessageBox.question(self, "Вы уверены?", f"Удалить категорию: {category}?")
        if result == QMessageBox.StandardButton.Yes:
            with self.con:
                self.con.execute('''
                    DELETE FROM categories
                    WHERE title = ?;
                ''', (category,))
            self.loadCategories()

class Tasks(QWidget, tasksForm):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.con = sqlite3.connect(DATABASE_NAME)
        createTables(self.con)
        self.con.execute("PRAGMA foreign_keys = 1")
        self.loadTasks()
        self.loadCategories()
        self.tasksList.itemClicked.connect(self.taskDetail)
        self.addTaskButton.clicked.connect(self.addTask)
        self.deleteTaskButton.clicked.connect(self.deleteTask)
        self.filterCategory.currentTextChanged.connect(self.loadTasks)
        # вывод данных и подключение сигналов виджетов
        # ...
        self.categoriesButton.clicked.connect(self.showCategories)

    def loadTasks(self):
        self.tasksList.clear()
        category = self.filterCategory.currentText()
        if category == '':
            result = self.con.execute('''
                SELECT title, done FROM tasks;
            ''').fetchall()

            for i in result:
                task = QListWidgetItem(i[0])
                task.setCheckState(Qt.CheckState.Checked if i[1] else Qt.CheckState.Unchecked)
                self.tasksList.addItem(task)
        else:
            category_id = self.con.execute('''
                SELECT id FROM categories
                WHERE title = ?
            ''', (category,)).fetchone()[0]
            result = self.con.execute('''
                SELECT title, done FROM tasks
                WHERE category_id = ?;
            ''', (category_id,)).fetchall()
            for i in result:
                task = QListWidgetItem(i[0])
                task.setCheckState(Qt.CheckState.Checked if i[1] else Qt.CheckState.Unchecked)
                self.tasksList.addItem(task)


    def loadCategories(self):
        self.filterCategory.clear()
        self.selectCategory.clear()
        result = self.con.execute('''
            SELECT title FROM categories;
        ''').fetchall()

        self.filterCategory.addItem(None)
        for i in result:
            self.filterCategory.addItem(i[0])
            self.selectCategory.addItem(i[0])

    def taskDetail(self, item):
        result = self.con.execute('''
            SELECT tasks.title, tasks.description, categories.title
            FROM tasks
            JOIN categories ON tasks.category_id = categories.id
            WHERE tasks.title = ?;
        ''', (item.text(),)).fetchall()

        r = result[0]
        self.taskTitle.setText(r[0])
        self.taskDescription.setText(r[1])
        self.selectCategory.setCurrentText(r[2])

        if item.checkState() == Qt.CheckState.Checked:
            done = 1
        else:
            done = 0

        with self.con:
            self.con.execute('''
                UPDATE tasks
                SET done = ?
                WHERE title = ?;
            ''', (done, item.text()))

    def addTask(self):
        task_title = self.taskTitle.text()
        task_desc = self.taskDescription.placeholderText()
        category = self.selectCategory.currentText()
        task_category = self.con.execute('''
            SELECT id FROM categories
            WHERE title = ?;
        ''', (category,)).fetchone()[0]

        with self.con:
            self.con.execute('''
                INSERT INTO tasks(title, description, done, category_id)
                VALUES (?, ?, 0, ?);
            ''', (task_title, task_desc, task_category))
        self.loadTasks()

    def deleteTask(self):
        title = self.tasksList.currentItem().text()
        task_id = self.con.execute('''
            SELECT id FROM tasks
            WHERE title = ?;
        ''', (title,)).fetchone()[0]

        result = QMessageBox.question(self, "Вы уверены?", f"Удалить задачу {title}?")

        if result == QMessageBox.StandardButton.Yes:
            with self.con:
                self.con.execute('''
                    DELETE FROM tasks
                    WHERE id = ?;
                ''', (task_id,))
        self.loadTasks()

    def showCategories(self):
        self.categoriesWindow = Categories(self.con)
        self.categoriesWindow.exec()
        self.loadTasks()
        self.loadCategories()


if __name__ == '__main__':
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    window = Tasks()
    window.show()
    sys.exit(app.exec())
