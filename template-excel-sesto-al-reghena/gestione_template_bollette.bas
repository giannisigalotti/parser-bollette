Attribute VB_Name = "GestioneTemplateBollette"
Option Explicit

Public Sub AggiornaFogliFabbricati()
    Const SHEET_FABBRICATI As String = "Fabbricati"
    Const SHEET_TEMPLATE As String = "_TemplateFabbricato"
    Const FIRST_DATA_ROW As Long = 2

    Dim wb As Workbook
    Dim wsFab As Worksheet
    Dim wsTemplate As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim sheetName As String
    Dim podValue As String
    Dim generatedSheets As Collection

    On Error GoTo CleanFail

    Set wb = ThisWorkbook
    Set wsFab = wb.Worksheets(SHEET_FABBRICATI)
    Set wsTemplate = wb.Worksheets(SHEET_TEMPLATE)
    Set generatedSheets = New Collection

    Application.ScreenUpdating = False

    AllineaFoglioCalcoloDaElettricitaInterno False
    CancellaFogliFabbricatiInterno False

    lastRow = wsFab.Cells(wsFab.Rows.Count, "A").End(xlUp).Row

    For r = FIRST_DATA_ROW To lastRow
        sheetName = Trim(CStr(wsFab.Cells(r, "A").Value))
        podValue = Trim(CStr(wsFab.Cells(r, "E").Value))
        If Len(sheetName) > 0 And Len(podValue) > 0 Then
            sheetName = NomeFoglioDaProgressivo(sheetName)
            wsTemplate.Copy After:=wb.Worksheets(wb.Worksheets.Count)
            With wb.Worksheets(wb.Worksheets.Count)
                .Visible = xlSheetVisible
                .Name = sheetName
                .Range("A2:S13").ClearContents
                .Range("A2").Formula2Local = "=FILTRO(Calcolo!V:AN;Calcolo!A:A=Fabbricati!E" & r & ")"
            End With
            generatedSheets.Add sheetName
        End If
    Next r

    wsFab.Activate
    Application.ScreenUpdating = True

    MsgBox "Fogli fabbricati generati: " & generatedSheets.Count, vbInformation
    Exit Sub

CleanFail:
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    MsgBox "Errore durante la generazione dei fogli fabbricati: " & Err.Description, vbExclamation
End Sub

Public Sub CancellaFogliFabbricati()
    CancellaFogliFabbricatiInterno True
End Sub

Public Sub AllineaFoglioCalcoloDaElettricita()
    AllineaFoglioCalcoloDaElettricitaInterno True
End Sub

Private Sub CancellaFogliFabbricatiInterno(ByVal mostraMessaggio As Boolean)
    Const SHEET_FABBRICATI As String = "Fabbricati"
    Const FIRST_DATA_ROW As Long = 2

    Dim wb As Workbook
    Dim wsFab As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim sheetName As String
    Dim deletedCount As Long

    On Error GoTo CleanFail

    Set wb = ThisWorkbook
    Set wsFab = wb.Worksheets(SHEET_FABBRICATI)

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    lastRow = wsFab.Cells(wsFab.Rows.Count, "A").End(xlUp).Row

    For r = FIRST_DATA_ROW To lastRow
        sheetName = NomeFoglioDaProgressivo(CStr(wsFab.Cells(r, "A").Value))
        If Len(sheetName) > 0 Then
            If SheetExists(sheetName, wb) Then
                wb.Worksheets(sheetName).Delete
                deletedCount = deletedCount + 1
            End If
        End If
    Next r

    Application.DisplayAlerts = True
    Application.ScreenUpdating = True

    If mostraMessaggio Then
        MsgBox "Fogli fabbricati cancellati: " & deletedCount, vbInformation
    End If
    Exit Sub

CleanFail:
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    MsgBox "Errore durante la cancellazione dei fogli fabbricati: " & Err.Description, vbExclamation
End Sub

Private Sub AllineaFoglioCalcoloDaElettricitaInterno(ByVal mostraMessaggio As Boolean)
    Const SHEET_CALCOLO As String = "Calcolo"
    Const TEMPLATE_ROW As Long = 2
    Const FIRST_GENERATED_ROW As Long = 3

    Dim wb As Workbook
    Dim wsElettricita As Worksheet
    Dim wsCalcolo As Worksheet
    Dim targetRows As Long
    Dim lastCalcRow As Long
    Dim lastCalcCol As Long
    Dim r As Long
    Dim sourceRange As Range
    Dim targetRange As Range
    Dim firstRowToClear As Long

    On Error GoTo CleanFail

    Set wb = ThisWorkbook
    If Not SheetExists("Elettricit" & ChrW(224), wb) Then
        Err.Raise vbObjectError + 1000, , "Foglio non trovato: Elettricit" & ChrW(224) & ". Fogli presenti: " & ElencoFogli(wb)
    End If
    If Not SheetExists(SHEET_CALCOLO, wb) Then
        Err.Raise vbObjectError + 1001, , "Foglio non trovato: " & SHEET_CALCOLO & ". Fogli presenti: " & ElencoFogli(wb)
    End If
    Set wsElettricita = wb.Worksheets("Elettricit" & ChrW(224))
    Set wsCalcolo = wb.Worksheets(SHEET_CALCOLO)

    Application.ScreenUpdating = False

    targetRows = LastUsedRow(wsElettricita)
    If targetRows < TEMPLATE_ROW Then targetRows = TEMPLATE_ROW

    lastCalcCol = LastUsedColumn(wsCalcolo)
    If lastCalcCol < 1 Then lastCalcCol = 1

    lastCalcRow = LastUsedRow(wsCalcolo)
    If lastCalcRow < 1 Then lastCalcRow = 1

    Set sourceRange = wsCalcolo.Range(wsCalcolo.Cells(TEMPLATE_ROW, 1), wsCalcolo.Cells(TEMPLATE_ROW, lastCalcCol))
    If targetRows >= FIRST_GENERATED_ROW Then
        For r = FIRST_GENERATED_ROW To targetRows
            Set targetRange = wsCalcolo.Range(wsCalcolo.Cells(r, 1), wsCalcolo.Cells(r, lastCalcCol))
            sourceRange.Copy Destination:=targetRange
        Next r
    End If
    Application.CutCopyMode = False

    lastCalcRow = LastUsedRow(wsCalcolo)
    If lastCalcRow > targetRows Then
        firstRowToClear = targetRows + 1
        If firstRowToClear < FIRST_GENERATED_ROW Then firstRowToClear = FIRST_GENERATED_ROW
        wsCalcolo.Range(wsCalcolo.Rows(firstRowToClear), wsCalcolo.Rows(lastCalcRow)).ClearContents
    End If

    Application.ScreenUpdating = True
    If mostraMessaggio Then
        MsgBox "Foglio Calcolo allineato a Elettricità: " & targetRows & " righe.", vbInformation
    End If
    Exit Sub

CleanFail:
    Application.ScreenUpdating = True
    MsgBox "Errore durante l'allineamento del foglio Calcolo: " & Err.Description, vbExclamation
End Sub

Private Function SheetExists(ByVal sheetName As String, ByVal wb As Workbook) As Boolean
    Dim ws As Worksheet
    SheetExists = False
    For Each ws In wb.Worksheets
        If ws.Name = sheetName Then
            SheetExists = True
            Exit Function
        End If
    Next ws
End Function

Private Function NomeFoglioDaProgressivo(ByVal rawName As String) As String
    Dim value As String
    value = Trim(rawName)
    If IsNumeric(value) Then
        value = Format(CLng(value), "00")
    End If
    value = Replace(value, "/", "-")
    value = Replace(value, "\", "-")
    value = Replace(value, "?", "")
    value = Replace(value, "*", "")
    value = Replace(value, "[", "(")
    value = Replace(value, "]", ")")
    value = Replace(value, ":", "-")
    NomeFoglioDaProgressivo = Left(value, 31)
End Function

Private Function LastUsedRow(ByVal ws As Worksheet) As Long
    Dim found As Range
    Set found = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    If found Is Nothing Then
        LastUsedRow = 0
    Else
        LastUsedRow = found.Row
    End If
End Function

Private Function LastUsedColumn(ByVal ws As Worksheet) As Long
    Dim found As Range
    Set found = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)
    If found Is Nothing Then
        LastUsedColumn = 0
    Else
        LastUsedColumn = found.Column
    End If
End Function

Private Function ElencoFogli(ByVal wb As Workbook) As String
    Dim ws As Worksheet
    Dim names As String
    For Each ws In wb.Worksheets
        If Len(names) > 0 Then
            names = names & ", "
        End If
        names = names & ws.Name
    Next ws
    ElencoFogli = names
End Function
