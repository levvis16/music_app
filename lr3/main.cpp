/*
 * Лабораторная работа №3. Рекурсия. Бинарные деревья.
 * Задача 20. Дано бинарное дерево. Вывести сумму значений всех листьев.
 *
 * Лист — узел, у которого нет ни левого, ни правого потомка.
 *
 * Сумма считается рекурсивно:
 *   - пустое поддерево даёт 0;
 *   - лист возвращает собственное значение;
 *   - внутренний узел возвращает сумму левого и правого поддеревьев.
 *
 * Сборка:
 *   g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 -o lab3 main.cpp
 *   cl /std:c++17 /EHsc /utf-8 main.cpp
 */

#include <cerrno>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <queue>
#include <sstream>
#include <string>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#endif

struct Node {
    int data;
    Node* left;
    Node* right;

    explicit Node(int value) : data(value), left(nullptr), right(nullptr) {}
};

enum class ReadStatus { Ok, EndOfInput };

void destroyTree(Node* node) {
    if (node == nullptr) {
        return;
    }
    destroyTree(node->left);
    destroyTree(node->right);
    delete node;
}

void clearInputLine() {
    std::cin.clear();
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
}

ReadStatus readInt(const std::string& prompt, int& value) {
    while (true) {
        std::cout << prompt;
        if (std::cin >> value) {
            return ReadStatus::Ok;
        }
        if (std::cin.eof()) {
            return ReadStatus::EndOfInput;
        }
        std::cout << "Ожидалось целое число.\n";
        clearInputLine();
    }
}

ReadStatus askYesNo(const std::string& prompt, bool& answer) {
    while (true) {
        std::cout << prompt << " (y/n): ";
        std::string token;
        if (!(std::cin >> token)) {
            if (std::cin.eof()) {
                return ReadStatus::EndOfInput;
            }
            clearInputLine();
            continue;
        }
        if (token == "y" || token == "Y" || token == "д" || token == "Д" ||
            token == "yes" || token == "да") {
            answer = true;
            return ReadStatus::Ok;
        }
        if (token == "n" || token == "N" || token == "н" || token == "Н" ||
            token == "no" || token == "нет") {
            answer = false;
            return ReadStatus::Ok;
        }
        std::cout << "Введите y или n.\n";
    }
}

// Рекурсивный диалог: для каждого узла запрашиваются значение и наличие потомков.
Node* buildInteractive(int depth, bool& ok) {
    const std::string pad(static_cast<std::size_t>(depth) * 2, ' ');
    int value = 0;
    if (readInt(pad + "Введите значение узла: ", value) != ReadStatus::Ok) {
        ok = false;
        return nullptr;
    }

    Node* node = new Node(value);

    bool hasLeft = false;
    if (askYesNo(pad + "Левый потомок узла " + std::to_string(value) + "?", hasLeft) !=
        ReadStatus::Ok) {
        destroyTree(node);
        ok = false;
        return nullptr;
    }
    if (hasLeft) {
        node->left = buildInteractive(depth + 1, ok);
        if (!ok) {
            destroyTree(node);
            return nullptr;
        }
    }

    bool hasRight = false;
    if (askYesNo(pad + "Правый потомок узла " + std::to_string(value) + "?", hasRight) !=
        ReadStatus::Ok) {
        destroyTree(node);
        ok = false;
        return nullptr;
    }
    if (hasRight) {
        node->right = buildInteractive(depth + 1, ok);
        if (!ok) {
            destroyTree(node);
            return nullptr;
        }
    }

    return node;
}

bool parseIntStrict(const std::string& token, int& value) {
    if (token.empty()) {
        return false;
    }
    errno = 0;
    char* end = nullptr;
    const long parsed = std::strtol(token.c_str(), &end, 10);
    if (end == token.c_str() || *end != '\0' || errno == ERANGE) {
        return false;
    }
    if (parsed < std::numeric_limits<int>::min() || parsed > std::numeric_limits<int>::max()) {
        return false;
    }
    value = static_cast<int>(parsed);
    return true;
}

bool isNullToken(const std::string& token) {
    return token == "*" || token == "null" || token == "NULL" || token == "nil";
}

// Обход по уровням: пустой узел записывается как *.
// Пример: 8 3 10 1 6 * 14 * * 4 7 13
bool buildFromLevelOrder(const std::string& line, Node*& root, std::string& error) {
    std::istringstream input(line);
    std::vector<std::string> tokens;
    std::string token;
    while (input >> token) {
        if (!token.empty() && token.back() == ',') {
            token.pop_back();
        }
        if (token.empty()) {
            error = "Пустой элемент в строке дерева.";
            return false;
        }
        tokens.push_back(token);
    }
    if (tokens.empty()) {
        error = "Строка пустая. Введите хотя бы корень или *.";
        return false;
    }
    if (isNullToken(tokens[0])) {
        root = nullptr;
        return true;
    }

    int rootValue = 0;
    if (!parseIntStrict(tokens[0], rootValue)) {
        error = "Не удалось прочитать корень: \"" + tokens[0] + "\".";
        return false;
    }

    Node* newRoot = new Node(rootValue);
    std::queue<Node*> parents;
    parents.push(newRoot);

    std::size_t index = 1;
    while (!parents.empty() && index < tokens.size()) {
        Node* parent = parents.front();
        parents.pop();

        for (int child = 0; child < 2 && index < tokens.size(); ++child) {
            const std::string& item = tokens[index++];
            if (isNullToken(item)) {
                continue;
            }
            int value = 0;
            if (!parseIntStrict(item, value)) {
                destroyTree(newRoot);
                error = "Некорректное значение узла: \"" + item + "\". Пустой узел — *.";
                return false;
            }
            Node* created = new Node(value);
            if (child == 0) {
                parent->left = created;
            } else {
                parent->right = created;
            }
            parents.push(created);
        }
    }

    root = newRoot;
    return true;
}

/*
 * Демонстрационное дерево. Листья: 1, 4, 7, 13. Сумма = 25.
 *
 *         8
 *       /   \
 *      3     10
 *     / \      \
 *    1   6     14
 *       / \    /
 *      4   7  13
 */
Node* makeSampleTree() {
    Node* root = new Node(8);
    root->left = new Node(3);
    root->right = new Node(10);
    root->left->left = new Node(1);
    root->left->right = new Node(6);
    root->left->right->left = new Node(4);
    root->left->right->right = new Node(7);
    root->right->right = new Node(14);
    root->right->right->left = new Node(13);
    return root;
}

bool isLeaf(const Node* node) {
    return node != nullptr && node->left == nullptr && node->right == nullptr;
}

// Основная функция задачи.
long long sumOfLeaves(const Node* node) {
    if (node == nullptr) {
        return 0;
    }
    if (isLeaf(node)) {
        return node->data;
    }
    return sumOfLeaves(node->left) + sumOfLeaves(node->right);
}

void collectLeaves(const Node* node, std::vector<int>& leaves) {
    if (node == nullptr) {
        return;
    }
    if (isLeaf(node)) {
        leaves.push_back(node->data);
        return;
    }
    collectLeaves(node->left, leaves);
    collectLeaves(node->right, leaves);
}

void printBranch(const Node* node, const std::string& prefix, bool isLast, bool isRoot) {
    if (node == nullptr) {
        return;
    }

    if (!isRoot) {
        std::cout << prefix << (isLast ? "`-- " : "|-- ");
    }
    std::cout << node->data;
    if (isLeaf(node)) {
        std::cout << "  (лист)";
    }
    std::cout << '\n';

    const std::string childPrefix = isRoot ? "" : prefix + (isLast ? "    " : "|   ");
    const bool hasLeft = node->left != nullptr;
    const bool hasRight = node->right != nullptr;
    if (hasLeft) {
        printBranch(node->left, childPrefix, !hasRight, false);
    }
    if (hasRight) {
        printBranch(node->right, childPrefix, true, false);
    }
}

void printTree(const Node* node) {
    printBranch(node, "", true, true);
}

void printSum(const Node* root) {
    if (root == nullptr) {
        std::cout << "Дерево пусто. Сумма значений листьев: 0\n";
        return;
    }

    std::vector<int> leaves;
    collectLeaves(root, leaves);
    std::cout << "Листья:";
    for (int value : leaves) {
        std::cout << ' ' << value;
    }
    std::cout << "\nСумма значений листьев: " << sumOfLeaves(root) << '\n';
}

void printMenu() {
    std::cout << "\n1. Построить дерево рекурсивно (диалог)\n";
    std::cout << "2. Построить дерево одной строкой (обход по уровням, * — пусто)\n";
    std::cout << "3. Загрузить демонстрационное дерево\n";
    std::cout << "4. Вывести дерево\n";
    std::cout << "5. Вывести листья и их сумму\n";
    std::cout << "0. Выход\n";
}

int runSelfCheck() {
    int failures = 0;
    auto expect = [&failures](const std::string& name, long long actual, long long expected) {
        if (actual != expected) {
            std::cerr << "FAIL " << name << ": получено " << actual << ", ожидалось " << expected
                      << '\n';
            ++failures;
        }
    };

    expect("пустое дерево", sumOfLeaves(nullptr), 0);

    Node* single = new Node(42);
    expect("один узел", sumOfLeaves(single), 42);
    destroyTree(single);

    Node* sample = makeSampleTree();
    expect("демонстрационное дерево", sumOfLeaves(sample), 25);
    std::vector<int> sampleLeaves;
    collectLeaves(sample, sampleLeaves);
    const std::vector<int> expectedLeaves{1, 4, 7, 13};
    if (sampleLeaves != expectedLeaves) {
        std::cerr << "FAIL список листьев демонстрационного дерева\n";
        ++failures;
    }
    destroyTree(sample);

    Node* chain = new Node(1);
    chain->left = new Node(2);
    chain->left->left = new Node(3);
    expect("левая цепочка", sumOfLeaves(chain), 3);
    destroyTree(chain);

    Node* negatives = new Node(0);
    negatives->left = new Node(-5);
    negatives->right = new Node(8);
    negatives->right->right = new Node(2);
    expect("отрицательные листья", sumOfLeaves(negatives), -3);
    destroyTree(negatives);

    Node* parsed = nullptr;
    std::string error;
    if (!buildFromLevelOrder("8 3 10 1 6 * 14 * * 4 7 13", parsed, error) ||
        sumOfLeaves(parsed) != 25) {
        std::cerr << "FAIL разбор строки дерева: " << error << '\n';
        ++failures;
    }
    destroyTree(parsed);
    parsed = nullptr;

    if (!buildFromLevelOrder("*", parsed, error) || parsed != nullptr || sumOfLeaves(parsed) != 0) {
        std::cerr << "FAIL пустая строка дерева\n";
        ++failures;
    }
    destroyTree(parsed);
    parsed = nullptr;

    if (!buildFromLevelOrder("1 * 3", parsed, error) || sumOfLeaves(parsed) != 3) {
        std::cerr << "FAIL только правый потомок\n";
        ++failures;
    }
    destroyTree(parsed);
    parsed = nullptr;

    if (buildFromLevelOrder("1 abc *", parsed, error)) {
        std::cerr << "FAIL некорректный токен был принят\n";
        ++failures;
        destroyTree(parsed);
    }

    if (failures == 0) {
        std::cout << "Самопроверка пройдена.\n";
        return 0;
    }
    std::cerr << "Ошибок: " << failures << '\n';
    return 1;
}

void setupConsole() {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif
}

int main(int argc, char* argv[]) {
    setupConsole();

    if (argc > 1 && std::string(argv[1]) == "--self-check") {
        return runSelfCheck();
    }

    std::cout << "Лабораторная работа №3. Рекурсия. Бинарные деревья.\n";
    std::cout << "Задача 20. Сумма значений всех листьев бинарного дерева.\n";
    std::cout << "Пример строки для пункта 2: 8 3 10 1 6 * 14 * * 4 7 13\n";

    Node* root = nullptr;
    while (true) {
        printMenu();
        int choice = 0;
        if (readInt("Выбор: ", choice) != ReadStatus::Ok) {
            destroyTree(root);
            std::cout << '\n';
            return 0;
        }

        switch (choice) {
        case 1: {
            std::cout << "Построение начинается с корня.\n";
            bool ok = true;
            Node* built = buildInteractive(0, ok);
            if (!ok) {
                destroyTree(root);
                std::cout << "\nВвод прерван.\n";
                return 0;
            }
            destroyTree(root);
            root = built;
            break;
        }
        case 2: {
            std::cout << "Введите узлы сверху вниз, слева направо. Пустой узел — *.\n";
            std::cout << "Строка: ";
            std::string line;
            std::getline(std::cin >> std::ws, line);
            if (!std::cin) {
                destroyTree(root);
                return 0;
            }
            Node* built = nullptr;
            std::string error;
            if (!buildFromLevelOrder(line, built, error)) {
                std::cout << error << '\n';
                break;
            }
            destroyTree(root);
            root = built;
            std::cout << "Дерево построено.\n";
            break;
        }
        case 3:
            destroyTree(root);
            root = makeSampleTree();
            std::cout << "Загружено дерево. Листья 1, 4, 7 и 13, сумма 25.\n";
            break;
        case 4:
            if (root == nullptr) {
                std::cout << "Дерево пусто.\n";
            } else {
                printTree(root);
            }
            break;
        case 5:
            printSum(root);
            break;
        case 0:
            destroyTree(root);
            return 0;
        default:
            std::cout << "Нет такого пункта.\n";
            break;
        }
    }
}
