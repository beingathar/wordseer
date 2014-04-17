import os

from flask import render_template, request
from werkzeug import secure_filename

from app import app
from .. import forms
from ..models import session, Unit, Project

PROJECT_ROUTE = "/projects/"

def allowed_file(filename):
    return os.path.splitext(filename)[1] in app.config["ALLOWED_EXTENSIONS"]

@app.route(PROJECT_ROUTE, methods=["GET", "POST"])
def projects():
    """
    This controller handles projects. It includes a form at the top to
    create a new project, and under the form the page has a listing of
    already created projects owned by the user.
    """
    form = forms.ProjectCreateForm()

    if request.method == "POST" and form.validate():
        #TODO: is this secure? maybe not
        project = Project(name=form.name.data)
        project.save()

    projects = Project.all().all()

    return render_template("project_list.html", form=form, projects=projects)

@app.route(PROJECT_ROUTE + "<proj_id>", methods=["GET", "POST"])
def project_show(proj_id):
    """
    Show the files contained in a specific project. It also allows the user
    to upload a new document, much like projects().

    :param int proj_id: The ID of the desired project.
    """

    if request.method == "POST":
        uploaded_file = request.files["uploaded_file"]
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            dest_path = os.path.join(app.config["UPLOAD_DIR"],
                filename)
            uploaded_file.save(dest_path)
            #TODO: send the user somewhere useful?
            unit = Unit(path=dest_path, project=proj_id)
            unit.save()

    form = forms.DocumentUploadForm()

    file_info = {}
    file_objects = session.query(Unit).filter(Unit.project == proj_id).\
        filter(Unit.path != None).all()
    for file_object in file_objects:
        file_info[file_object.id] = os.path.split(file_object.path)[1]

    project = session.query(Project).filter(Project.id == proj_id).one()

    return render_template("document_list.html", files=file_info,
        project=project, form=form)
