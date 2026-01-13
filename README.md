# Skippatore
Programma che permette di skippare qualsiasi contenuto "skippabile" su qualsiasi sito di video.

LIBRERIE DA INSTALLARE:

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import json
import os
import threading
import time
from PIL import ImageTk
import pyautogui
import pytesseract
from PIL import Image, ImageEnhance, ImageOps
import ctypes
import win32api
import win32con
import mss
from screeninfo import get_monitors
import sys
